import { AliceHUD } from "../components/AliceHUD";
import type { AliceAPIConfig } from "@alice/api";

const config: AliceAPIConfig = {
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  wsURL: process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws",
  guardianURL: process.env.NEXT_PUBLIC_GUARDIAN_URL || "http://localhost:8787",
  timeout: 10000,
  retries: 3,
};

export default function HomePage() {
  return (
    <main>
      <AliceHUD config={config} />
    </main>
  );
}
