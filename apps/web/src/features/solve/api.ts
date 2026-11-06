/**
 * Test çözme ve oturum yönetimi API işlemlerini TanStack Query hook'larıyla sunar.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { client } from "../../lib/api/client";
import { ApiError } from "../../lib/api/problem";
import type {
  AnswerRequest,
  AnswerResponse,
  BlockResponse,
  ExamSummary,
  HintResponse,
  SessionCompletionResponse,
  SessionResponse,
  SessionReviewResponse,
} from "./types";

export const solveKeys = {
  tests: ["solve", "tests"] as const,
  /** Test oturumu sorgu anahtarını üretir. */
  session: (testId: number) => ["solve", "session", testId] as const,
  /** Oturum sonucu sorgu anahtarını üretir. */
  result: (sessionId: number) => ["solve", "result", sessionId] as const,
  /** Oturum incelemesi sorgu anahtarını üretir. */
  review: (sessionId: number) => ["solve", "review", sessionId] as const,
  /** Alıntı bloğu sorgu anahtarını üretir. */
  block: (id: number) => ["solve", "block", id] as const,
};
/**
 * Tamamlanmış oturumun net ve kazanım özetini sunucudan getirir.
 */
export function useSessionResult(sessionId: number) {
  return useQuery<SessionCompletionResponse, ApiError>({
    queryKey: solveKeys.result(sessionId),
    /** Sonucu GET /api/sessions/{id}/result ucundan okur. */
    queryFn: async (): Promise<SessionCompletionResponse> => {
      const { data, error, response } = await client.GET("/api/sessions/{id}/result", {
        params: { path: { id: sessionId } },
      });
      const status = response.status;

      if (error || !data) {
        throw new ApiError(error, status);
      }

      return data;
    },
  });
}

/**
 * Öğrencinin çözebileceği testleri sunucudan getirir.
 */
export function useTests() {
  return useQuery<ExamSummary[], ApiError>({
    queryKey: solveKeys.tests,
    /** Test listesini GET /api/tests ucundan okur. */
    queryFn: async (): Promise<ExamSummary[]> => {
      const { data, error, response } = await client.GET("/api/tests");
      const status = response.status;

      if (error || !data) {
        throw new ApiError(error, status);
      }

      return data;
    },
  });
}

/**
 * Test oturumunu başlatır veya yarım kalan oturumu kaldığı yerden getirir.
 */
export function useStartSession() {
  return useMutation<SessionResponse, ApiError, number>({
    /** Test oturumunu POST /api/tests/{id}/sessions ucundan başlatır. */
    mutationFn: async (testId: number): Promise<SessionResponse> => {
      const { data, error, response } = await client.POST("/api/tests/{id}/sessions", {
        params: { path: { id: testId } },
      });
      const status = response.status;

      if (error || !data) {
        throw new ApiError(error, status);
      }

      return data;
    },
  });
}

interface SubmitAnswerParams {
  sessionId: number;
  questionId: number;
  request: AnswerRequest;
}

/**
 * Öğrencinin seçtiği cevabı kaydeder ve doğru yanıt ile kazanımları döner.
 */
export function useSubmitAnswer() {
  return useMutation<AnswerResponse, ApiError, SubmitAnswerParams>({
    /** Cevabı PUT /api/sessions/{id}/answers/{questionId} ucuna gönderir. */
    mutationFn: async ({
      sessionId,
      questionId,
      request,
    }: SubmitAnswerParams): Promise<AnswerResponse> => {
      const { data, error, response } = await client.PUT(
        "/api/sessions/{id}/answers/{questionId}",
        {
          params: { path: { id: sessionId, questionId } },
          body: request,
        },
      );
      const status = response.status;

      if (error || !data) {
        throw new ApiError(error, status);
      }

      return data;
    },
  });
}

/**
 * Test oturumunu tamamlar ve net ile kazanım bazlı özet sonucunu döner.
 */
export function useCompleteSession() {
  const queryClient = useQueryClient();

  return useMutation<SessionCompletionResponse, ApiError, number>({
    /** Sonuç sayfası yeniden istemesin diye sonucu önbelleğe yazar. */
    onSuccess: (result, sessionId) => {
      queryClient.setQueryData(solveKeys.result(sessionId), result);
    },
    /** Oturumu POST /api/sessions/{id}/complete ucundan tamamlar. */
    mutationFn: async (sessionId: number): Promise<SessionCompletionResponse> => {
      const { data, error, response } = await client.POST("/api/sessions/{id}/complete", {
        params: { path: { id: sessionId } },
      });
      const status = response.status;

      if (error || !data) {
        throw new ApiError(error, status);
      }

      return data;
    },
  });
}

/**
 * Alıntı kartında gösterilecek içerik bloğunu getirir.
 */
export function useBlock(id: number | null) {
  return useQuery<BlockResponse, ApiError>({
    queryKey: id ? solveKeys.block(id) : ["solve", "block", "null"],
    enabled: id !== null && id > 0,
    /** Belirtilen bloğu GET /api/blocks/{id} ucundan okur. */
    queryFn: async (): Promise<BlockResponse> => {
      if (!id) {
        throw new Error("Geçersiz blok kimliği.");
      }
      const { data, error, response } = await client.GET("/api/blocks/{id}", {
        params: { path: { id } },
      });
      const status = response.status;

      if (error || !data) {
        throw new ApiError(error, status);
      }

      return data;
    },
  });
}

/**
 * Sorunun cevabını söylemeden öğrenciye yön gösteren ipucunu getirir.
 */
export function useHint() {
  return useMutation<HintResponse, ApiError, number>({
    /** İpucunu GET /api/questions/{id}/hint ucundan okur. */
    mutationFn: async (questionId: number): Promise<HintResponse> => {
      const { data, error, response } = await client.GET("/api/questions/{id}/hint", {
        params: { path: { id: questionId } },
      });
      const status = response.status;

      if (error || !data) {
        throw new ApiError(error, status);
      }

      return data;
    },
  });
}

/**
 * Tamamlanmış oturumun sorularını doğru şık ve cevaplarla tek istekte getirir.
 */
export function useSessionReview(sessionId: number) {
  return useQuery<SessionReviewResponse, ApiError>({
    queryKey: solveKeys.review(sessionId),
    staleTime: Infinity,
    /** İncelemeyi GET /api/sessions/{id}/review ucundan okur. */
    queryFn: async (): Promise<SessionReviewResponse> => {
      const { data, error, response } = await client.GET("/api/sessions/{id}/review", {
        params: { path: { id: sessionId } },
      });
      const status = response.status;

      if (error || !data) {
        throw new ApiError(error, status);
      }

      return data;
    },
  });
}
