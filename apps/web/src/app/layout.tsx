import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Alice v2 - Enterprise AI Assistant',
  description: 'Advanced AI-powered assistant with Swedish language support',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="sv">
      <body>{children}</body>
    </html>
  )
}