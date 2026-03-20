import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { Toaster } from "sonner";

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'TAC-PMC CRM | Financial Management System',
  description: 'Enterprise Construction Financial Management System for TAC-PMC',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  console.log('RootLayout: rendering children');
  return (
    <html lang="en">
      <body className={inter.className}>
        <Toaster richColors position="top-right" />
        {children}
      </body>
    </html>
  );
}
