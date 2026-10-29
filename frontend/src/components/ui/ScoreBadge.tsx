import { ShieldAlert, ShieldCheck, ShieldQuestion } from "lucide-react";
import { Badge } from "./Badge";

export type ScamLevel = "safe" | "suspicious" | "scam";

export function scamLevel(score: number): ScamLevel {
  if (score < 30) return "safe";
  if (score <= 60) return "suspicious";
  return "scam";
}

const META: Record<ScamLevel, { label: string; tone: "green" | "yellow" | "red"; Icon: typeof ShieldCheck }> = {
  safe: { label: "безпечно", tone: "green", Icon: ShieldCheck },
  suspicious: { label: "підозріло", tone: "yellow", Icon: ShieldQuestion },
  scam: { label: "скам", tone: "red", Icon: ShieldAlert },
};

export function ScoreBadge({ score }: { score: number }) {
  const level = scamLevel(score);
  const { label, tone, Icon } = META[level];
  return (
    <span title={`scam_score: ${score}`}>
      <Badge tone={tone}>
        <Icon size={12} />
        {label}
      </Badge>
    </span>
  );
}
