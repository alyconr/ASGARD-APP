"use client";

import { toast } from "sonner";

type NotificationOptions = Readonly<{
  description?: string;
}>;

function buildToastOptions(options?: NotificationOptions): NotificationOptions {
  return {
    description: options?.description,
  };
}

export const notify = {
  error(message: string, options?: NotificationOptions): void {
    toast.error(message, buildToastOptions(options));
  },
  info(message: string, options?: NotificationOptions): void {
    toast.info(message, buildToastOptions(options));
  },
  success(message: string, options?: NotificationOptions): void {
    toast.success(message, buildToastOptions(options));
  },
  warning(message: string, options?: NotificationOptions): void {
    toast.warning(message, buildToastOptions(options));
  },
};
