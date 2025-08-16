import './globals.css'
import { ToastProvider } from "@/context/ToastContext";
import { Toaster } from "@/components/Toaster";

export const metadata = {
  title: 'Hirevision - AI Interview Platform',
  description: 'Boost your hiring process with AI solution',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>
        <ToastProvider>
          {children}
          <Toaster />
        </ToastProvider>
      </body>
    </html>
  )
}
