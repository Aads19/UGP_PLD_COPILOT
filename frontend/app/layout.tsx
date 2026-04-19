import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "UGP PLD Copilot",
  description: "A public research chatbot for PLD literature exploration with source-grounded answers."
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
