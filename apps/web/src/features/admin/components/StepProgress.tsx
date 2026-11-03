/**
 * Kaynak hazırlık hattının adımlarını segmentli ilerleme çubuğu olarak gösterir.
 */

/** Sunucunun bildirdiği adım sayısı kadar segment çizer. */
export default function StepProgress({
  stepIndex,
  totalSteps,
  isFailed,
}: {
  stepIndex: number;
  totalSteps: number;
  isFailed: boolean;
}) {
  const completedColor = isFailed ? "bg-destructive" : "bg-emerald-600 dark:bg-emerald-500";

  return (
    <div className="flex gap-1">
      {Array.from({ length: totalSteps }, (_, index) => (
        <div
          key={index}
          className={`h-1.5 w-4 rounded-full transition-colors ${
            index < stepIndex ? completedColor : "bg-muted"
          }`}
          data-testid="step-segment"
        />
      ))}
    </div>
  );
}
