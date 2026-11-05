/**
 * Öğrenci paneli API tiplerine verilen kısa adları ve arayüz arayüzlerini tanımlar.
 */
import type { components } from "../../lib/api/schema";

export type DashboardResponse = components["schemas"]["DashboardResponse"];
export type DashboardSummary = components["schemas"]["DashboardSummary"];
export type DashboardActiveSession = components["schemas"]["DashboardActiveSession"];
export type DashboardFailedOutcome = components["schemas"]["DashboardFailedOutcome"];
export type DashboardUnitAccuracy = components["schemas"]["DashboardUnitAccuracy"];
export type DashboardErrorTypeCount = components["schemas"]["DashboardErrorTypeCount"];
