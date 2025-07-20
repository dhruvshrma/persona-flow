import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Persona Flow',
  description: 'Persona Flow is a tool for agentic testing and discovery for your product.',
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
