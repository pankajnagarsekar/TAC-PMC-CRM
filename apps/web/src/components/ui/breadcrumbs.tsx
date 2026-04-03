"use client"

import * as React from "react"
import Link from "next/link"
import { ChevronRight, Home } from "lucide-react"

interface BreadcrumbItem {
    label: string
    href?: string
}

interface BreadcrumbsProps {
    items: BreadcrumbItem[]
}

export function Breadcrumbs({ items }: BreadcrumbsProps) {
    return (
        <nav className="flex items-center text-[13px] font-medium text-zinc-500">
            <Link href="/admin/dashboard" className="hover:text-foreground transition-colors">
                <Home size={14} />
            </Link>
            {items.map((item, index) => (
                <React.Fragment key={index}>
                    <ChevronRight size={14} className="mx-2 text-muted-foreground/30" />
                    {item.href ? (
                        <Link href={item.href} className="hover:text-foreground transition-colors">
                            {item.label}
                        </Link>
                    ) : (
                        <span className="text-zinc-900 dark:text-zinc-100 font-semibold">{item.label}</span>
                    )}
                </React.Fragment>
            ))}
        </nav>
    )
}
