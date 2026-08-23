import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'MedCore — AI Clinical Decision Support',
  description: 'Эмнэлзүйн шийдвэр дэмжих AI систем',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="mn" className="h-full antialiased">
      <body className="min-h-full">{children}</body>
    </html>
  )
}
