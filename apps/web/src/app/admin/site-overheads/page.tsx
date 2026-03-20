"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function SiteOverheadsRedirect() {
    const router = useRouter();
    useEffect(() => {
        router.replace("/admin/site-operations?tab=funds");
    }, [router]);
    return null;
}
