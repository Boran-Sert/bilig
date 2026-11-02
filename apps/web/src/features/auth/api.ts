/**
 * Kimlik doğrulama API işlemlerini TanStack Query hook'larıyla sunar.
 */
import {
  type Query,
  type QueryClient,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { client } from "../../lib/api/client";
import { ApiError } from "../../lib/api/problem";
import { HTTP_STATUS_UNAUTHORIZED } from "../../lib/constants";
import type { CurrentUser, LoginRequest, RegisterRequest } from "./types";

export const authKeys = {
  me: ["auth", "me"] as const,
};

/**
 * Önceki kullanıcının önbelleğini silip oturumdaki kullanıcıyı yazar.
 * @param queryClient Uygulamanın sorgu istemcisi.
 * @param user Oturumdaki kullanıcı; çıkışta null.
 */
function replaceSessionCache(queryClient: QueryClient, user: CurrentUser | null) {
  queryClient.removeQueries({ predicate: isUserDataQuery });
  queryClient.setQueryData(authKeys.me, user);
}

/**
 * Sorgunun oturum sorgusu dışında kullanıcıya ait veri olup olmadığını söyler.
 * @param query İncelenen sorgu.
 * @returns Oturum sorgusu değilse true.
 */
function isUserDataQuery(query: Query): boolean {
  return query.queryKey[0] !== authKeys.me[0];
}

/**
 * Sunucu oturumun düştüğünü bildirdiğinde önbellekteki oturumu kapatır.
 * @param queryClient Uygulamanın sorgu istemcisi.
 * @param error Sorgu ya da işlemden gelen hata.
 */
export function clearSessionOnUnauthorized(queryClient: QueryClient, error: unknown) {
  if (error instanceof ApiError && error.status === HTTP_STATUS_UNAUTHORIZED) {
    replaceSessionCache(queryClient, null);
  }
}

/**
 * Oturumdaki kullanıcıyı getirir; oturum yoksa null döndürür.
 */
export function useMe() {
  return useQuery({
    queryKey: authKeys.me,
    /** Mevcut kullanıcıyı sunucudan okur. */
    queryFn: async (): Promise<CurrentUser | null> => {
      const { data, error, response } = await client.GET("/api/me");
      const status = response.status;

      if (status === HTTP_STATUS_UNAUTHORIZED) {
        return null;
      }

      if (error || !data) {
        throw new ApiError(error, status);
      }

      return data;
    },
    retry: false,
  });
}

/**
 * Kullanıcıyı giriş bilgileriyle oturum açtırır.
 */
export function useLogin() {
  const queryClient = useQueryClient();

  return useMutation({
    /** Giriş isteğini gönderir. */
    mutationFn: async (input: LoginRequest) => {
      const { data, error, response } = await client.POST("/api/auth/login", { body: input });
      const status = response.status;

      if (error || !data) {
        throw new ApiError(error, status);
      }

      return data;
    },
    /** Önceki önbelleği silip yeni kullanıcıyı yazar. */
    onSuccess: (user) => {
      replaceSessionCache(queryClient, user);
    },
  });
}

/**
 * Yeni hesap oluşturur; sunucu aynı istekte oturumu açar.
 */
export function useRegister() {
  const queryClient = useQueryClient();

  return useMutation({
    /** Kayıt isteğini gönderir. */
    mutationFn: async (input: RegisterRequest) => {
      const { data, error, response } = await client.POST("/api/auth/register", { body: input });
      const status = response.status;

      if (error || !data) {
        throw new ApiError(error, status);
      }

      return data;
    },
    /** Önceki önbelleği silip yeni kullanıcıyı yazar. */
    onSuccess: (user) => {
      replaceSessionCache(queryClient, user);
    },
  });
}

/**
 * Oturumu kapatır ve kullanıcıya ait önbelleği siler.
 */
export function useLogout() {
  const queryClient = useQueryClient();

  return useMutation({
    /** Çıkış isteğini gönderir. */
    mutationFn: async () => {
      const { error, response } = await client.POST("/api/auth/logout");
      const status = response.status;

      if (error) {
        throw new ApiError(error, status);
      }
    },
    /** Önbellekteki bütün kullanıcı verisini siler. */
    onSuccess: () => {
      replaceSessionCache(queryClient, null);
    },
  });
}
