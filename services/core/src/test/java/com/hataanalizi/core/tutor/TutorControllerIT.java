package com.hataanalizi.core.tutor;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.authentication;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.csrf;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.asyncDispatch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.request;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.hataanalizi.core.TestcontainersConfiguration;
import com.hataanalizi.core.auth.AuthUser;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import org.springframework.test.web.servlet.request.RequestPostProcessor;
import reactor.core.publisher.Flux;

/** Tutor SSE uçlarının HTTP sözleşmesini ve PostgreSQL kayıtlarını doğrular. */
@ActiveProfiles("test")
@SpringBootTest
@AutoConfigureMockMvc
@Import(TestcontainersConfiguration.class)
class TutorControllerIT {

    private final JdbcTemplate jdbcTemplate;
    private final MockMvc mockMvc;
    private final TutorTestFixture fixture;

    @MockitoBean
    private AiClient aiClient;

    /** HTTP, veritabanı ve test veri üreticisini saklar. */
    @Autowired
    TutorControllerIT(JdbcTemplate jdbcTemplate, MockMvc mockMvc) {
        this.jdbcTemplate = jdbcTemplate;
        this.mockMvc = mockMvc;
        this.fixture = new TutorTestFixture(jdbcTemplate);
    }

    /** Python olaylarını sırayla iletir, tamamlanan yanıtı ve alıntıyı kaydeder. */
    @Test
    void streamsExplanationAndPersistsAssistantAndCitation() throws Exception {
        Long userId = fixture.insertUser();
        TutorTestFixture.AnsweredQuestion question = fixture.insertAnsweredQuestion(userId);
        Long blockId = fixture.insertContentBlock(userId);
        when(aiClient.streamExplanation(userId, question.questionId(), "A")).thenReturn(explanationEvents(blockId));

        String response = sendExplanation(userId, question);

        assertOrderedEvents(response, "delta", "citation", "citation", "delta", "done");
        assertExplanationPersisted(response, userId, question.questionId(), blockId);
        verify(aiClient).streamExplanation(userId, question.questionId(), "A");
    }

    /** Anlatım olaylarını iki kez yinelenen alıntıyla üretir. */
    private Flux<AiClient.StreamEvent> explanationEvents(Long blockId) {
        String citation = "{\"blockId\":" + blockId + ",\"sourceTitle\":\"TDE 12 Ders Kitabı\",\"page\":175}";
        return Flux.just(
                        new AiClient.StreamEvent("delta", "{\"text\":\"Küçük Ağa \"}"),
                        new AiClient.StreamEvent("citation", citation),
                        new AiClient.StreamEvent("citation", citation),
                        new AiClient.StreamEvent("delta", "{\"text\":\"tarihî romandır.\"}"),
                        new AiClient.StreamEvent("done", "{}"))
                .delayElements(Duration.ofMillis(2));
    }

    /** Anlatım gövdesinin, alıntısının ve done kimliklerinin veritabanına kaydını doğrular. */
    private void assertExplanationPersisted(String response, Long userId, Long questionId, Long blockId) {
        assertThat(response)
                .contains(
                        "{\"text\":\"Küçük Ağa \"}",
                        "{\"blockId\":" + blockId + ",\"sourceTitle\":\"TDE 12 Ders Kitabı\",\"page\":175}",
                        "{\"messageId\":",
                        "\"conversationId\":");
        Long conversationId = jdbcTemplate.queryForObject(
                "SELECT id FROM tutor_conversation WHERE user_id = ? AND question_id = ?",
                Long.class,
                userId,
                questionId);
        Long messageId = jdbcTemplate.queryForObject("""
                SELECT id FROM tutor_message
                WHERE tutor_conversation_id = ? AND role = 'ASSISTANT'
                """, Long.class, conversationId);
        assertThat(jdbcTemplate.queryForObject(
                        "SELECT content FROM tutor_message WHERE id = ?", String.class, messageId))
                .isEqualTo("Küçük Ağa tarihî romandır.");
        assertThat(jdbcTemplate.queryForObject("""
                        SELECT content_block_id FROM tutor_message_citation WHERE tutor_message_id = ?
                        """, Long.class, messageId)).isEqualTo(blockId);
        assertThat(response).contains("\"messageId\":" + messageId, "\"conversationId\":" + conversationId);
    }

    /** Öğrenci iletisini önce kaydeder ve sohbet yanıtını akıtır. */
    @Test
    void storesUserMessageBeforeStreamingChatResponse() throws Exception {
        Long userId = fixture.insertUser();
        Long conversationId = fixture.insertConversation(userId);
        when(aiClient.streamChat(conversationId, userId, false)).thenAnswer(invocation -> {
            assertThat(fixture.messageCount(conversationId)).isEqualTo(1);
            return Flux.just(
                            new AiClient.StreamEvent("delta", "{\"text\":\"Evet.\"}"),
                            new AiClient.StreamEvent("done", "{}"))
                    .delayElements(Duration.ofMillis(2));
        });

        String response = sendChat(userId, conversationId, "{\"text\":\"Devlet Ana da tarihî roman mı?\"}");

        assertOrderedEvents(response, "delta", "done");
        assertThat(response).contains("\"conversationId\":" + conversationId);
        assertThat(jdbcTemplate.queryForList("""
                        SELECT role, content FROM tutor_message
                        WHERE tutor_conversation_id = ? ORDER BY id
                        """, conversationId))
                .containsExactly(
                        java.util.Map.of("role", "USER", "content", "Devlet Ana da tarihî roman mı?"),
                        java.util.Map.of("role", "ASSISTANT", "content", "Evet."));
        verify(aiClient).streamChat(conversationId, userId, false);
    }

    /** Cevaplanmamış soruda sohbeti açar, doğru şıkkı saklama bayrağıyla Python'a iletir. */
    @Test
    void startsChatForUnansweredQuestionAndHidesAnswer() throws Exception {
        Long userId = fixture.insertUser();
        TutorTestFixture.AnsweredQuestion question = fixture.insertUnansweredQuestion(userId);
        when(aiClient.streamChat(anyLong(), eq(userId), eq(true)))
                .thenReturn(Flux.just(
                        new AiClient.StreamEvent("delta", "{\"text\":\"Önce metne bak.\"}"),
                        new AiClient.StreamEvent("done", "{}")));

        String response = sendStartChat(userId, startChatBody(question, "Bu soruda ne isteniyor?"));

        assertOrderedEvents(response, "delta", "done");
        Long conversationId = jdbcTemplate.queryForObject(
                "SELECT id FROM tutor_conversation WHERE user_id = ? AND question_id = ?",
                Long.class,
                userId,
                question.questionId());
        assertThat(jdbcTemplate.queryForList(
                        "SELECT role, content FROM tutor_message WHERE tutor_conversation_id = ? ORDER BY id",
                        conversationId))
                .containsExactly(
                        java.util.Map.of("role", "USER", "content", "Bu soruda ne isteniyor?"),
                        java.util.Map.of("role", "ASSISTANT", "content", "Önce metne bak."));
        verify(aiClient).streamChat(conversationId, userId, true);
    }

    /** Başka öğrencinin oturumu için sohbet açmayı Python'a gitmeden reddeder. */
    @Test
    void rejectsStartChatForAnotherUsersSession() throws Exception {
        Long ownerId = fixture.insertUser();
        Long otherUserId = fixture.insertUser();
        TutorTestFixture.AnsweredQuestion question = fixture.insertUnansweredQuestion(ownerId);

        mockMvc.perform(post("/api/tutor/chats")
                        .with(student(otherUserId))
                        .with(csrf())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(startChatBody(question, "Merhaba")))
                .andExpect(status().isNotFound());

        verify(aiClient, never()).streamChat(anyLong(), anyLong(), org.mockito.ArgumentMatchers.anyBoolean());
        assertThat(jdbcTemplate.queryForObject(
                        "SELECT count(*) FROM tutor_conversation WHERE user_id = ?", Integer.class, otherUserId))
                .isZero();
    }

    /** Python akış hatasını error olayıyla iletir ve yarım asistan mesajı kaydetmez. */
    @Test
    void pythonErrorDoesNotPersistPartialAssistantMessage() throws Exception {
        Long userId = fixture.insertUser();
        TutorTestFixture.AnsweredQuestion question = fixture.insertAnsweredQuestion(userId);
        when(aiClient.streamExplanation(userId, question.questionId(), "A"))
                .thenReturn(Flux.just(
                                new AiClient.StreamEvent("delta", "{\"text\":\"Yarım yanıt\"}"),
                                new AiClient.StreamEvent("error", "{\"title\":\"AI stream failed\",\"status\":503}"))
                        .delayElements(Duration.ofMillis(2)));

        String response = sendExplanation(userId, question);

        assertOrderedEvents(response, "delta", "error");
        assertThat(response).contains("\"status\":503", "\"code\":\"AI_UNAVAILABLE\"");
        Long conversationId = jdbcTemplate.queryForObject(
                "SELECT id FROM tutor_conversation WHERE user_id = ? AND question_id = ?",
                Long.class,
                userId,
                question.questionId());
        assertThat(jdbcTemplate.queryForObject("""
                        SELECT count(*) FROM tutor_message
                        WHERE tutor_conversation_id = ? AND role = 'ASSISTANT'
                        """, Integer.class, conversationId))
                .isZero();
    }

    /** Python soru bulunamadı hatasını NOT_FOUND Problem Details olayıyla iletir. */
    @Test
    void pythonNotFoundErrorUsesNotFoundCode() throws Exception {
        Long userId = fixture.insertUser();
        TutorTestFixture.AnsweredQuestion question = fixture.insertAnsweredQuestion(userId);
        when(aiClient.streamExplanation(userId, question.questionId(), "A"))
                .thenReturn(Flux.just(
                                new AiClient.StreamEvent("error", "{\"title\":\"Question not found\",\"status\":404}"))
                        .delayElements(Duration.ofMillis(2)));

        String response = sendExplanation(userId, question);

        assertOrderedEvents(response, "error");
        assertThat(response).contains("\"status\":404", "\"code\":\"NOT_FOUND\"");
        Long conversationId = jdbcTemplate.queryForObject(
                "SELECT id FROM tutor_conversation WHERE user_id = ? AND question_id = ?",
                Long.class,
                userId,
                question.questionId());
        assertThat(jdbcTemplate.queryForObject("""
                        SELECT count(*) FROM tutor_message
                        WHERE tutor_conversation_id = ? AND role = 'ASSISTANT'
                        """, Integer.class, conversationId))
                .isZero();
    }

    /** Python bağlantısı kesilince hata olayı yollar ve yarım yanıtı kaydetmez. */
    @Test
    void disconnectDoesNotPersistPartialAssistantMessage() throws Exception {
        Long userId = fixture.insertUser();
        TutorTestFixture.AnsweredQuestion question = fixture.insertAnsweredQuestion(userId);
        when(aiClient.streamExplanation(userId, question.questionId(), "A"))
                .thenReturn(Flux.concat(
                        Flux.just(new AiClient.StreamEvent("delta", "{\"text\":\"Yarım yanıt\"}"))
                                .delayElements(Duration.ofMillis(2)),
                        Flux.error(new IllegalStateException("Connection closed"))));

        String response = sendExplanation(userId, question);

        assertOrderedEvents(response, "delta", "error");
        assertThat(response).contains("\"status\":503", "\"code\":\"AI_UNAVAILABLE\"");
        Long conversationId = jdbcTemplate.queryForObject(
                "SELECT id FROM tutor_conversation WHERE user_id = ? AND question_id = ?",
                Long.class,
                userId,
                question.questionId());
        assertThat(jdbcTemplate.queryForObject("""
                        SELECT count(*) FROM tutor_message
                        WHERE tutor_conversation_id = ? AND role = 'ASSISTANT'
                        """, Integer.class, conversationId))
                .isZero();
    }

    /** Başka öğrencinin oturumu için anlatım akışını ve AI çağrısını reddeder. */
    @Test
    void rejectsAnotherUsersSession() throws Exception {
        Long ownerId = fixture.insertUser();
        Long otherUserId = fixture.insertUser();
        TutorTestFixture.AnsweredQuestion question = fixture.insertAnsweredQuestion(ownerId);

        mockMvc.perform(post("/api/tutor/explanations")
                        .with(student(otherUserId))
                        .with(csrf())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(explanationBody(question)))
                .andExpect(status().isNotFound())
                .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_PROBLEM_JSON));

        verify(aiClient, never()).streamExplanation(otherUserId, question.questionId(), "A");
        assertThat(jdbcTemplate.queryForObject(
                        "SELECT count(*) FROM tutor_conversation WHERE user_id = ?", Integer.class, otherUserId))
                .isZero();
    }

    /** Anlatım uç isteğini SSE cevabı olarak tamamlar. */
    private String sendExplanation(Long userId, TutorTestFixture.AnsweredQuestion question) throws Exception {
        MvcResult result = mockMvc.perform(post("/api/tutor/explanations")
                        .with(student(userId))
                        .with(csrf())
                        .contentType(MediaType.APPLICATION_JSON)
                        .accept(MediaType.TEXT_EVENT_STREAM)
                        .content(explanationBody(question)))
                .andExpect(request().asyncStarted())
                .andReturn();
        return mockMvc.perform(asyncDispatch(result))
                .andExpect(status().isOk())
                .andExpect(content().contentTypeCompatibleWith(MediaType.TEXT_EVENT_STREAM))
                .andReturn()
                .getResponse()
                .getContentAsString(StandardCharsets.UTF_8);
    }

    /** Sohbet başlatma uç isteğini SSE cevabı olarak tamamlar. */
    private String sendStartChat(Long userId, String requestBody) throws Exception {
        MvcResult result = mockMvc.perform(post("/api/tutor/chats")
                        .with(student(userId))
                        .with(csrf())
                        .contentType(MediaType.APPLICATION_JSON)
                        .accept(MediaType.TEXT_EVENT_STREAM)
                        .content(requestBody))
                .andExpect(request().asyncStarted())
                .andReturn();
        return mockMvc.perform(asyncDispatch(result))
                .andExpect(status().isOk())
                .andReturn()
                .getResponse()
                .getContentAsString(StandardCharsets.UTF_8);
    }

    /** Sohbet başlatma isteğinin JSON gövdesini üretir. */
    private String startChatBody(TutorTestFixture.AnsweredQuestion question, String text) {
        return "{\"sessionId\":" + question.sessionId() + ",\"questionId\":" + question.questionId() + ",\"text\":\""
                + text + "\"}";
    }

    /** Sohbet uç isteğini SSE cevabı olarak tamamlar. */
    private String sendChat(Long userId, Long conversationId, String requestBody) throws Exception {
        MvcResult result = mockMvc.perform(post("/api/tutor/conversations/{id}/messages", conversationId)
                        .with(student(userId))
                        .with(csrf())
                        .contentType(MediaType.APPLICATION_JSON)
                        .accept(MediaType.TEXT_EVENT_STREAM)
                        .content(requestBody))
                .andExpect(request().asyncStarted())
                .andReturn();
        return mockMvc.perform(asyncDispatch(result))
                .andExpect(status().isOk())
                .andExpect(content().contentTypeCompatibleWith(MediaType.TEXT_EVENT_STREAM))
                .andReturn()
                .getResponse()
                .getContentAsString(StandardCharsets.UTF_8);
    }

    /** Olay adlarının akışta beklenen sırayı koruduğunu doğrular. */
    private void assertOrderedEvents(String response, String... eventNames) {
        int previousIndex = -1;
        for (String eventName : eventNames) {
            int currentIndex = response.indexOf("event:" + eventName, previousIndex + 1);
            assertThat(currentIndex).isGreaterThan(previousIndex);
            previousIndex = currentIndex;
        }
    }

    /** Açıklama uç isteğinin JSON gövdesini üretir. */
    private String explanationBody(TutorTestFixture.AnsweredQuestion question) {
        return "{\"sessionId\":" + question.sessionId() + ",\"questionId\":" + question.questionId() + "}";
    }

    /** İstek için test öğrencisinin kimliğini hazırlar. */
    private RequestPostProcessor student(Long userId) {
        AuthUser authUser = new AuthUser(userId, "student@example.test", "STUDENT");
        var authentication = new UsernamePasswordAuthenticationToken(
                authUser, null, List.of(new SimpleGrantedAuthority("ROLE_STUDENT")));
        return authentication(authentication);
    }
}
