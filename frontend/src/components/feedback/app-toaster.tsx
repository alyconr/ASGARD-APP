"use client";

import { Toaster } from "sonner";

export function AppToaster(): React.JSX.Element {
  return (
    <Toaster
      closeButton
      richColors
      position="top-right"
      toastOptions={{
        duration: 4200,
        classNames: {
          toast: "sena-toast",
          title: "sena-toast-title",
          description: "sena-toast-description",
        },
      }}
    />
  );
}
