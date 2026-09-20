import { TriangleAlert, Trash2 } from "lucide-react";

import Button from "./Button";
import SectionLabel from "./SectionLabel";

function ConfirmDialog({
  open = false,
  title,
  description,
  text,
  onCancel,
  onConfirm,
}) {
  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-foreground/35 px-5">
      <div className="w-full max-w-md border border-border bg-card p-6 shadow-xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <SectionLabel>Confirm action</SectionLabel>

            <h2 className="text-xl font-semibold">
              {title}
            </h2>

            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              {description || text}
            </p>
          </div>

          <TriangleAlert
            className="shrink-0 text-accent"
            size={20}
          />
        </div>

        <div className="mt-7 flex justify-end gap-2">
          <Button
            variant="outline"
            onClick={onCancel}
          >
            Cancel
          </Button>

          <Button
            variant="copper"
            onClick={onConfirm}
          >
            <Trash2 size={15} />
            Delete record
          </Button>
        </div>
      </div>
    </div>
  );
}

export default ConfirmDialog;