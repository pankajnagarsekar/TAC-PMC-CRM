import useSWR from 'swr';
import { fetcher } from '@/lib/api';
import { Vendor } from '@tac-pmc/types';
import { useMemo, useCallback } from 'react';

/**
 * Hook to provide a mapping of vendor IDs to their readable names.
 * Used to resolve vendor names in grids and lists where only IDs are present.
 */
export function useVendorNames() {
    const { data: vendors, isLoading, error } = useSWR<Vendor[]>('/api/v1/vendors/', fetcher);

    const vendorMap = useMemo(() => {
        const map: Record<string, string> = {};
        if (vendors && Array.isArray(vendors)) {
            vendors.forEach((v) => {
                const vid = v._id;
                if (vid) {
                    map[vid] = v.name;
                }
            });
        }
        return map;
    }, [vendors]);

    const getVendorName = useCallback((id?: string) => {
        if (!id) return '-';
        if (isLoading) return 'Loading...';
        return vendorMap[id] || "Unknown Vendor";
    }, [vendorMap, isLoading]);

    return {
        vendorMap,
        getVendorName,
        isLoading,
        error
    };
}
