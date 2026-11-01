/**
 * Kimlik doğrulama API işlemlerini yönetir.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { client } from "../../lib/api/client";
import { getProblemMessage } from "../../lib/api/problem";

export const authKeys = {
  me: ["auth", "me"] as const,
};

/**
 *
 */
export function useMe() {
  return useQuery({
    queryKey: authKeys.me,
    /**
     *
     */
    queryFn: async () => {
      const { data, error } = await client.GET("/api/me");

      if (error) {
        throw new Error(getProblemMessage(error));
      }

      return data;
    },
    retry: false,
  });
}

/**
 *
 */
export function useLogin() {
  const queryClient = useQueryClient();

  return useMutation({
    /**
     *
     */
    mutationFn: async (input: { email: string; password: string; rememberMe: boolean }) => {
      const { data, error } = await client.POST("/api/auth/login", {
        body: input,
      });

      if (error) {
        throw new Error(getProblemMessage(error));
      }

      return data;
    },
    /**
     *
     */
    onSuccess: (user) => {
      queryClient.setQueryData(authKeys.me, user);
    },
  });
}

/**
 *
 */
export function useRegister() {
  return useMutation({
    /**
     *
     */
    mutationFn: async (input: {
      email: string;
      password: string;
      displayName: string;
      grade: number;
      explainStyle: "SIMPLE" | "EXAMPLES" | "STEP_BY_STEP";
    }) => {
      const { data, error } = await client.POST("/api/auth/register", {
        body: input,
      });

      if (error) {
        throw new Error(getProblemMessage(error));
      }

      return data;
    },
  });
}

/**
 *
 */
export function useLogout() {
  const queryClient = useQueryClient();

  return useMutation({
    /**
     *
     */
    mutationFn: async () => {
      const { error } = await client.POST("/api/auth/logout");

      if (error) {
        throw new Error(getProblemMessage(error));
      }
    },
    /**
     *
     */
    onSuccess: () => {
      queryClient.setQueryData(authKeys.me, null);
    },
  });
}
