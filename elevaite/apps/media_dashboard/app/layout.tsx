import { ColorContextProvider } from "@repo/ui/contexts";
import type { Metadata } from "next";
import { SessionProvider } from "next-auth/react";
import { Inter } from "next/font/google";
import { auth } from "../auth";
import { AppLayout } from "./components/AppLayout";
import "./globals.css";

// Use Inter with expanded options for better typography control
const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "Command Agent Analytics",
  description: "ElevAIte's Chatbot, ready to answer your questions!",
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>): Promise<JSX.Element> {
  const session = await auth();
  const breadcrumbs: Record<string, { label: string; link: string }> = {
    home: {
      label: "Command Agent Analytics",
      link: "/",
    },
  };

  return (
    <html lang="en">
      <body className={`${inter.className} ${inter.variable} antialiased`}>
        <SessionProvider session={session}>
          <ColorContextProvider>
            <AppLayout breadcrumbs={breadcrumbs}>
              {children}
            </AppLayout>
          </ColorContextProvider>
        </SessionProvider>
      </body>
    </html>
  );
}