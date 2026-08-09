import { createFileRoute } from "@tanstack/react-router";
import { DekcExplorer } from "@/components/dekc-explorer";

export const Route = createFileRoute("/")({
  component: Home,
});

function Home() {
  return <DekcExplorer />;
}
