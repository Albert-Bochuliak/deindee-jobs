import { X } from "lucide-react";
import type { InputHTMLAttributes } from "react";

interface Props extends InputHTMLAttributes<HTMLInputElement> {
  value: string | number;
  onClear: () => void;
  /** extra classes on the positioning wrapper (sizing goes here, e.g. w-32) */
  wrapperClassName?: string;
}

/** Input with an × clear button that appears on hover while it has text. */
export function ClearableInput({
  value,
  onClear,
  wrapperClassName,
  className,
  ...rest
}: Props) {
  const hasValue = String(value) !== "";
  return (
    <div className={`group relative ${wrapperClassName ?? ""}`}>
      <input
        {...rest}
        value={value}
        className={`${className ?? ""} w-full pr-7`}
      />
      {hasValue && (
        <button
          type="button"
          tabIndex={-1}
          aria-label="Очистити"
          onClick={onClear}
          className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-0.5 text-slate-500 opacity-0 transition-opacity hover:bg-slate-700 hover:text-slate-200 group-hover:opacity-100"
        >
          <X size={14} />
        </button>
      )}
    </div>
  );
}
