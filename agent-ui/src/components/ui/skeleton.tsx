import { cn } from "@/lib/utils";
// FIXME  MC8yOmFIVnBZMlhsc3JQbGxydm5uN002YjJWVllnPT06ZmUxMWI0YWE=

function Skeleton({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("animate-pulse rounded-md bg-muted", className)}
      {...props}
    />
  );
}
// NOTE  MS8yOmFIVnBZMlhsc3JQbGxydm5uN002YjJWVllnPT06ZmUxMWI0YWE=

export { Skeleton };
