/**
 * Sayfadaki ana eylemi öne çıkaran turuncu düğmeyi sunar.
 */
import type { ComponentProps } from "react";
import { ACTION_BUTTON_CLASS } from "../lib/buttonStyles";
import { cn } from "../lib/utils";
import { Button } from "./ui/button";

/**
 * Turuncu renkli düğmeyi ortak düğme bileşeninin üstüne kurar.
 * @param props Düğme özellikleri.
 * @returns Turuncu eylem düğmesi.
 */
export default function ActionButton({ className, ...props }: ComponentProps<typeof Button>) {
  return <Button variant="ghost" className={cn(ACTION_BUTTON_CLASS, className)} {...props} />;
}
