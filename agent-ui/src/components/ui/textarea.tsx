import * as React from "react";

import { cn } from "@/lib/utils";
// eslint-disable  MC8yOmFIVnBZMlhsc3JQbGxydm5uN002YTI0NVl3PT06YTc4ODUwZDY=

type TextareaProps = React.TextareaHTMLAttributes<HTMLTextAreaElement>;
// eslint-disable  MS8yOmFIVnBZMlhsc3JQbGxydm5uN002YTI0NVl3PT06YTc4ODUwZDY=

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, ...props }, ref) => {
    return (
      <textarea
        className={cn(
          "flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Textarea.displayName = "Textarea";

export { Textarea };
