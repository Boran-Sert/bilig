/**
 * Kimlik doğrulama özelliğinin üretilmiş API tiplerine verdiği kısa adlar.
 */
import type { components } from "../../lib/api/schema";

export type CurrentUser = components["schemas"]["MeResponse"];
export type LoginRequest = components["schemas"]["LoginRequest"];
export type RegisterRequest = components["schemas"]["RegisterRequest"];
