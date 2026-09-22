import type { Metadata } from "next";
import { MasterDashboard } from "@/features/dashboard/master-dashboard";

export const metadata: Metadata = { title: "ASGARD | Dashboard maestro SENA" };

export default function DashboardPage(): React.JSX.Element {
  return <MasterDashboard />;
}
