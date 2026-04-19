"use client";

import React, { forwardRef, useImperativeHandle, useRef, useState, useEffect } from 'react';
import { CustomCellEditorProps } from 'ag-grid-react';

/**
 * High-Precision Numeric Cell Editor (Phase 3 Hardening)
 * Enforces strict character masking and numeric integrity.
 */
export const NumericCellEditor = forwardRef((props: CustomCellEditorProps, ref) => {
    const [value, setValue] = useState(props.value);
    const inputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        // Focus and select content on mount
        inputRef.current?.focus();
        inputRef.current?.select();
    }, []);

    const onKeyDown = (event: React.KeyboardEvent) => {
        const key = event.key;

        // Allow navigation and modification keys
        if (
            key === 'Backspace' ||
            key === 'Delete' ||
            key === 'Tab' ||
            key === 'Escape' ||
            key === 'Enter' ||
            key === 'ArrowLeft' ||
            key === 'ArrowRight' ||
            key === 'Home' ||
            key === 'End' ||
            (event.ctrlKey && (key === 'a' || key === 'c' || key === 'v'))
        ) {
            return;
        }

        // Block 'e', '+', '-', and other non-numeric chars
        // Only allow one decimal point
        if (key === '.') {
            if (typeof value === 'string' && value.includes('.')) {
                event.preventDefault();
            }
            return;
        }

        if (!/^[0-9]$/.test(key)) {
            event.preventDefault();
        }
    };

    const onChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        setValue(event.target.value);
    };

    // AG Grid expected interface
    useImperativeHandle(ref, () => {
        return {
            getValue() {
                if (value === '' || value === null || value === undefined) return 0;
                const parsed = parseFloat(value);
                return isNaN(parsed) ? 0 : parsed;
            },
            isCancelBeforeStart() {
                return false;
            },
            isCancelAfterEnd() {
                return false;
            }
        };
    });

    return (
        <div className="flex w-full h-full items-center px-2 bg-white dark:bg-zinc-900 border-2 border-orange-500 rounded shadow-lg z-50">
            <input
                ref={inputRef}
                className="w-full bg-transparent border-none outline-none font-mono text-zinc-900 dark:text-white px-1"
                value={value ?? ''}
                onChange={onChange}
                onKeyDown={onKeyDown}
                type="text"
            />
        </div>
    );
});

NumericCellEditor.displayName = 'NumericCellEditor';
