/**
 * Soru çözme ve test oturumu API tiplerini tanımlar.
 */
import type { components } from "../../lib/api/schema";

export type SessionResponse = components["schemas"]["SessionResponse"];
export type SessionQuestion = components["schemas"]["SessionQuestionResponse"];
export type QuestionContent = components["schemas"]["QuestionContent"];
export type QuestionOption = components["schemas"]["QuestionOption"];
export type Block = components["schemas"]["Block"];
export type AnswerRequest = components["schemas"]["AnswerRequest"];
export type AnswerResponse = components["schemas"]["AnswerResponse"];
export type Outcome = components["schemas"]["Outcome"];
export type ExamSummary = components["schemas"]["ExamSummaryResponse"];
export type SessionCompletionResponse = components["schemas"]["SessionCompletionResponse"];
export type SessionCompletionOutcome = components["schemas"]["SessionCompletionOutcome"];
