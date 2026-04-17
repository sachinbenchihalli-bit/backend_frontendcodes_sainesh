import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ReactQueryProvider, ThemeProviderWrapper } from "./providers";
import { SessionProvider } from "next-auth/react";
import { auth } from "../auth";
import { AppLayout } from "./components/AppLayout";
import { ColorContextProvider } from "@repo/ui/contexts";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Command Agent Workflows",
  description: "Campaign performance and analytics dashboard",
  icons: {
    icon: "/favicon.svg",
  },
};

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await auth();
  const breadcrumbs: Record<string, { label: string; link: string }> = {
    home: {
      label: "Command Agent Workflows",
      link: "",
    },
    campaigns: {
      label: "Campaigns",
      link: "/campaigns",
    },
    "insertion-orders": {
      label: "Insertion Orders",
      link: "/insertion-orders",
    },
  };

  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <SessionProvider session={session}>
          <ColorContextProvider>
            <ThemeProviderWrapper>
              <ReactQueryProvider>
                <TooltipProvider>
                  <Toaster />
                  <Sonner />
                  <AppLayout breadcrumbs={breadcrumbs}>
                    {children}
                  </AppLayout>
                </TooltipProvider>
              </ReactQueryProvider>
            </ThemeProviderWrapper>
          </ColorContextProvider>
        </SessionProvider>
      </body>
    </html>
  );
}
