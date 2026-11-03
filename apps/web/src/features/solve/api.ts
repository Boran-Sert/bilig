/**
 * Test çözme ve oturum yönetimi API işlemlerini TanStack Query hook'larıyla sunar.
 */
import { useMutation, useQuery } from "@tanstack/react-query";
import { client } from "../../lib/api/client";
import { ApiError } from "../../lib/api/problem";
import type { AnswerRequest, AnswerResponse, ExamSummary, SessionResponse } from "./types";

export const solveKeys = {
  tests: ["solve", "tests"] as const,
  /** Test oturumu sorgu anahtarını üretir. */
  session: (testId: number) => ["solve", "session", testId] as const,
};

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
