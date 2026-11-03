import type { Metadata } from "next";
// Self-hosted from npm so builds never depend on fetching Google Fonts.
import "@fontsource/ibm-plex-sans/400.css";
import "@fontsource/ibm-plex-sans/500.css";
import "@fontsource/ibm-plex-sans/600.css";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/500.css";

import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: { default: "CrediSure Ops Console", template: "%s · CrediSure Ops Console" },
  description: "Internal ops dashboard for onboarding, verification and provider health.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
