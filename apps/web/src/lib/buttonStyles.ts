/**
 * Bağlantıların düğme gibi görünmesi için ortak sınıf adlarını üretir.
 */
import { buttonVariants } from "../components/ui/button";
import { cn } from "./utils";

export const ACTION_BUTTON_CLASS =
  "h-10! rounded-xl! bg-action! px-5! font-semibold text-action-foreground! hover:bg-action-hover!";

/** Turuncu eylem düğmesi görünümlü bağlantı sınıfını üretir. */
export function actionLinkClass(extra?: string) {
  return cn(buttonVariants({ variant: "ghost" }), ACTION_BUTTON_CLASS, extra);
}

/** Lacivert dolgulu ya da çerçeveli düğme görünümlü bağlantı sınıfını üretir. */
export function linkButtonClass(variant: "default" | "outline" | "ghost", extra?: string) {
  return cn(buttonVariants({ variant }), "h-10 rounded-xl px-5", extra);
}
