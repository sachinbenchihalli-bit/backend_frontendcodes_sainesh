import React, { useState, useRef, useCallback } from "react";
import "./Table.scss";

export interface Column<T> {
    label: string;
    key: keyof T;
    render?: (value: T[keyof T], row: T) => React.ReactNode;
    width?: string;
    minWidth?: string;
    resizable?: boolean;
}

export interface ExpandableRowConfig<T> {
    render: (row: T) => React.ReactNode;
}

interface TableProps<T> {
    data: T[];
    columns: Column<T>[];
    title: string;
    showExportButton?: boolean;
    showPagination?: boolean;
    expandableRow?: ExpandableRowConfig<T>;
}

const Table = <T,>({ data, columns, _title, _showExportButton, showPagination, expandableRow }: TableProps<T>): React.ReactElement => {
    const [currentPage, setCurrentPage] = useState(1);
    const [itemsPerPage, setItemsPerPage] = useState(10);
    const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());
    const [columnWidths, setColumnWidths] = useState<Record<number, number>>({});
    const tableRef = useRef<HTMLTableElement>(null);
    const resizingRef = useRef<{ columnIndex: number; startX: number; startWidth: number } | null>(null);
    const totalPages = Math.ceil(data.length / itemsPerPage);

    const handlePageChange = (page: number): void => {
        setCurrentPage(page);
    };

    const toggleRowExpansion = (rowIndex: number): void => {
        const newExpandedRows = new Set(expandedRows);
        if (newExpandedRows.has(rowIndex)) {
            newExpandedRows.delete(rowIndex);
        } else {
            newExpandedRows.add(rowIndex);
        }
        setExpandedRows(newExpandedRows);
    };

    const handleMouseDown = useCallback((e: React.MouseEvent, columnIndex: number) => {
        e.preventDefault();
        e.stopPropagation();

        const startX = e.clientX;
        const table = tableRef.current;
        if (!table) return;

        const th = table.querySelectorAll('th')[columnIndex + (expandableRow ? 1 : 0)];
        const startWidth = th.offsetWidth;

        resizingRef.current = { columnIndex, startX, startWidth };

        // Add visual feedback
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';

        // Add a resize indicator line
        const resizeLine = document.createElement('div');
        resizeLine.id = 'resize-indicator';
        resizeLine.style.cssText = `
            position: fixed;
            top: 0;
            bottom: 0;
            width: 2px;
            background: #007bff;
            z-index: 9999;
            pointer-events: none;
            left: ${String(e.clientX)}px;
        `;
        document.body.appendChild(resizeLine);

        const handleMouseMove = (moveEvent: MouseEvent): void => {
            if (!resizingRef.current) return;

            const { columnIndex: resizeColumnIndex, startX: resizeStartX, startWidth: resizeStartWidth } = resizingRef.current;
            const deltaX = moveEvent.clientX - resizeStartX;
            const newWidth = Math.max(80, resizeStartWidth + deltaX);

            // Update resize indicator position
            const indicator = document.getElementById('resize-indicator');
            if (indicator) {
                indicator.style.left = `${String(moveEvent.clientX)}px`;
            }

            setColumnWidths(prev => ({
                ...prev,
                [resizeColumnIndex]: newWidth
            }));
        };

        const handleMouseUp = (): void => {
            resizingRef.current = null;
            document.body.style.cursor = '';
            document.body.style.userSelect = '';

            // Remove resize indicator
            const indicator = document.getElementById('resize-indicator');
            if (indicator) {
                document.body.removeChild(indicator);
            }

            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
        };

        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('mouseup', handleMouseUp);
    }, [expandableRow]);

    const getPageNumbers = (): (number | string)[] => {
        const pages: (number | string)[] = [];
        if (totalPages <= 10) {
            for (let i = 1; i <= totalPages; i++) pages.push(i);
        } else if (currentPage <= 3) {
            pages.push(1, 2, 3, 4, "...", totalPages);
        } else if (currentPage >= totalPages - 2) {
            pages.push(1, "...", totalPages - 3, totalPages - 2, totalPages - 1, totalPages);
        } else {
            pages.push(1, "...", currentPage - 1, currentPage, currentPage + 1, "...", totalPages);
        }
        return pages;
    };

    return (
        <div className="replacement-parts-container">
            <div className="table-wrapper">
                <table ref={tableRef}>
                    <thead>
                        <tr>
                            {expandableRow && (
                                <th style={{ width: '40px', minWidth: '40px' }}>
                                    <span style={{ fontSize: '12px', color: '#666' }}>▼</span>
                                </th>
                            )}
                            {columns.map((column, index) => (
                                <th
                                    key={`header-${column.label}-${String(index)}`}
                                    className={column.resizable !== false ? 'resizable' : ''}
                                    style={{
                                        width: columnWidths[index] ? `${String(columnWidths[index])}px` : column.width ?? 'auto',
                                        minWidth: column.minWidth ?? '80px',
                                        position: 'relative',
                                        maxWidth: columnWidths[index] ? `${String(columnWidths[index])}px` : 'none'
                                    }}
                                >
                                    <div style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'space-between',
                                        height: '100%',
                                        position: 'relative'
                                    }}>
                                        <span style={{
                                            display: 'block',
                                            overflow: 'hidden',
                                            textOverflow: 'ellipsis',
                                            flex: 1
                                        }}>
                                            {column.label}
                                        </span>
                                    </div>
                                    {column.resizable !== false && (
                                        <div
                                            className="resize-handle"
                                            role="button"
                                            tabIndex={0}
                                            style={{
                                                position: 'absolute',
                                                top: 0,
                                                right: '-2px',
                                                width: '4px',
                                                height: '100%',
                                                cursor: 'col-resize',
                                                background: 'transparent',
                                                zIndex: 10,
                                                borderRight: '1px solid transparent'
                                            }}
                                            onMouseDown={(e) => {
                                                handleMouseDown(e, index);
                                            }}
                                            onKeyDown={(e) => {
                                                if (e.key === 'Enter' || e.key === ' ') {
                                                    handleMouseDown(e as unknown as React.MouseEvent, index);
                                                }
                                            }}
                                            onMouseEnter={(e) => {
                                                (e.target as HTMLElement).style.borderRight = '1px solid #007bff';
                                                (e.target as HTMLElement).style.background = 'rgba(0, 123, 255, 0.1)';
                                            }}
                                            onMouseLeave={(e) => {
                                                (e.target as HTMLElement).style.borderRight = '1px solid transparent';
                                                (e.target as HTMLElement).style.background = 'transparent';
                                            }}
                                            onClick={(e) => {
                                                e.stopPropagation();
                                            }}
                                        />
                                    )}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {(showPagination ?
                            data.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage) :
                            data
                        ).map((row, rowIndex) => {
                            const actualRowIndex = showPagination ? (currentPage - 1) * itemsPerPage + rowIndex : rowIndex;
                            const isExpanded = expandedRows.has(actualRowIndex);

                            return (
                                <React.Fragment key={`row-${String(rowIndex)}`}>
                                    <tr
                                        className={expandableRow ? 'expandable-row' : ''}
                                        onClick={expandableRow ? () => {
                                            toggleRowExpansion(actualRowIndex);
                                        } : undefined}
                                    >
                                        {expandableRow && (
                                            <td className="expand-icon">
                                                <span className={`expand-arrow ${isExpanded ? 'expanded' : ''}`}>
                                                    ▶
                                                </span>
                                            </td>
                                        )}
                                        {columns.map((column, colIndex) => {
                                            const value = row[column.key];
                                            return (
                                                <td
                                                    key={`cell-${String(colIndex)}`}
                                                    className={column.key === 'query_id' || column.key === 'session_id' ? 'id-column' : ''}
                                                    style={{
                                                        width: columnWidths[colIndex] ? `${String(columnWidths[colIndex])}px` : column.width ?? 'auto',
                                                        minWidth: column.minWidth ?? '80px',
                                                        maxWidth: columnWidths[colIndex] ? `${String(columnWidths[colIndex])}px` : '300px',
                                                        position: 'relative'
                                                    }}
                                                    title={typeof value === 'string' ? value : ''}
                                                >
                                                    <div style={{
                                                        overflow: 'hidden',
                                                        textOverflow: 'ellipsis',
                                                        whiteSpace: 'nowrap',
                                                        width: '100%',
                                                        fontFamily: (column.key === 'query_id' || column.key === 'session_id') ? 'monospace' : 'inherit',
                                                        fontSize: (column.key === 'query_id' || column.key === 'session_id') ? '0.85em' : 'inherit'
                                                    }}>
                                                        {column.render ? column.render(value, row) : (value as React.ReactNode)}
                                                    </div>
                                                </td>
                                            );
                                        })}
                                    </tr>
                                    {expandableRow && isExpanded && (
                                        <tr className="expanded-content">
                                            <td colSpan={columns.length + 1} className="expanded-cell">
                                                {expandableRow.render(row)}
                                            </td>
                                        </tr>
                                    )}
                                </React.Fragment>
                            );
                        })}
                    </tbody>
                </table>
            </div>

            {showPagination && data.length > 0 && (
                <div className="pagination-container">
                    <div className="entries-info">
                        Showing {(currentPage - 1) * itemsPerPage + 1} to{" "}
                        {Math.min(currentPage * itemsPerPage, data.length)} of {data.length} entries
                    </div>

                    <div className="pagination-pages">
                        {getPageNumbers().map((page, index) => (
                            <button
                                key={`page-${String(index)}`}
                                type="button"
                                onClick={() => {
                                    if (typeof page === "number") {
                                        handlePageChange(page);
                                    }
                                }}
                                className={`pagination-page ${page === currentPage ? "active" : ""}`}
                                disabled={page === "..."}
                            >
                                {page}
                            </button>
                        ))}
                        <select
                            value={itemsPerPage}
                            onChange={(e) => {
                                setItemsPerPage(Number(e.target.value));
                                setCurrentPage(1);
                            }}
                            className="items-per-page"
                        >
                            {[10, 25, 50].map((num) => (
                                <option key={num} value={num}>
                                    {num} / page
                                </option>
                            ))}
                        </select>
                    </div>

                    <div className="pagination-buttons">
                        <button
                            type="button"
                            onClick={() => {
                                handlePageChange(currentPage - 1);
                            }}
                            disabled={currentPage === 1}
                            className="pagination-button"
                        >
                            &lt; Back
                        </button>
                        <button
                            type="button"
                            onClick={() => {
                                handlePageChange(currentPage + 1);
                            }}
                            disabled={currentPage === totalPages}
                            className="pagination-button"
                        >
                            Next &gt;
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default Table;

