import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Alice AI Assistant HUD',
  description: 'Next-generation AI assistant with Guardian protection',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="bg-[#030b10] text-cyan-100">{children}</body>
    </html>
  );
}
