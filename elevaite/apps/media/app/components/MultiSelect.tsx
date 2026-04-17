"use client";
import { useState, useRef, useEffect } from "react";
import { CommonButton, CommonFormLabels, ElevaiteIcons, type CommonSelectOption } from "@repo/ui/components";
import "./MultiSelect.scss";

export interface MultiSelectProps {
    label: string;
    options: CommonSelectOption[];
    selectedValues: string[];
    onChange: (values: string[]) => void;
    maxDisplayItems?: number;
    disabled?: boolean;
}

export function MultiSelect({
    label,
    options,
    selectedValues,
    onChange,
    maxDisplayItems = 2,
    disabled = false
}: MultiSelectProps): JSX.Element {
    const [isOpen, setIsOpen] = useState(false);
    const buttonRef = useRef<HTMLButtonElement | null>(null);
    const dropdownRef = useRef<HTMLDivElement | null>(null);

    // Merge predefined options with any selected values that aren't in the options
    const getAllOptions = (): CommonSelectOption[] => {
        const optionValues = options.map(opt => opt.value);
        const additionalOptions: CommonSelectOption[] = selectedValues
            .filter(value => !optionValues.includes(value))
            .map(value => ({ value, label: value }));

        return [...options, ...additionalOptions];
    };

    const handleToggle = () => {
        if (!disabled) {
            setIsOpen(!isOpen);
        }
    };

    const handleOptionToggle = (value: string) => {
        const newValues = selectedValues.includes(value)
            ? selectedValues.filter(v => v !== value)
            : [...selectedValues, value];
        onChange(newValues);
    };

    const getDisplayText = (): string => {
        if (selectedValues.length === 0) {
            return "No selected options";
        }
        
        const selectedLabels = selectedValues.map(value => {
            const option = options.find(opt => opt.value === value);
            return option?.label || value;
        });

        if (selectedLabels.length <= maxDisplayItems) {
            return selectedLabels.join(", ");
        } else {
            const displayItems = selectedLabels.slice(0, maxDisplayItems);
            const remainingCount = selectedLabels.length - maxDisplayItems;
            return `${displayItems.join(", ")} +${remainingCount} more`;
        }
    };

    // Handle click outside to close dropdown
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (
                dropdownRef.current && 
                !dropdownRef.current.contains(event.target as Node) &&
                buttonRef.current && 
                !buttonRef.current.contains(event.target as Node)
            ) {
                setIsOpen(false);
            }
        };

        if (isOpen) {
            document.addEventListener('mousedown', handleClickOutside);
            return () => document.removeEventListener('mousedown', handleClickOutside);
        }
    }, [isOpen]);

    return (
        <CommonFormLabels label={label}>
            <div className="multi-select-container">
                <CommonButton
                    passedRef={buttonRef}
                    className="multi-select-trigger"
                    onClick={handleToggle}
                    noBackground
                    disabled={disabled}
                >
                    <span className="multi-select-display-text">
                        {getDisplayText()}
                    </span>
                    <ElevaiteIcons.SVGChevron className={`multi-select-chevron ${isOpen ? 'rotated' : ''}`} />
                </CommonButton>

                {isOpen && (
                    <div ref={dropdownRef} className="multi-select-dropdown">
                        <div className="multi-select-options">
                            {(() => {
                                const allOptions = getAllOptions();
                                const predefinedOptions = allOptions.filter(opt => options.some(o => o.value === opt.value));
                                const customOptions = allOptions.filter(opt => !options.some(o => o.value === opt.value));

                                return (
                                    <>
                                        {predefinedOptions.map((option) => {
                                            const isSelected = selectedValues.includes(option.value);
                                            return (
                                                <div
                                                    key={option.value}
                                                    className="multi-select-option"
                                                    onClick={() => handleOptionToggle(option.value)}
                                                >
                                                    <input
                                                        type="checkbox"
                                                        checked={isSelected}
                                                        onChange={() => {}} // Handled by parent click
                                                        className="multi-select-checkbox"
                                                    />
                                                    <span className="multi-select-option-label">
                                                        {option.label || option.value}
                                                    </span>
                                                </div>
                                            );
                                        })}

                                        {customOptions.length > 0 && predefinedOptions.length > 0 && (
                                            <div className="multi-select-separator">
                                                <span>Custom Values</span>
                                            </div>
                                        )}

                                        {customOptions.map((option) => {
                                            const isSelected = selectedValues.includes(option.value);
                                            return (
                                                <div
                                                    key={option.value}
                                                    className="multi-select-option custom-option"
                                                    onClick={() => handleOptionToggle(option.value)}
                                                >
                                                    <input
                                                        type="checkbox"
                                                        checked={isSelected}
                                                        onChange={() => {}} // Handled by parent click
                                                        className="multi-select-checkbox"
                                                    />
                                                    <span className="multi-select-option-label">
                                                        {option.label || option.value}
                                                        <span className="custom-indicator"> (custom)</span>
                                                    </span>
                                                </div>
                                            );
                                        })}
                                    </>
                                );
                            })()}
                        </div>
                    </div>
                )}
            </div>
        </CommonFormLabels>
    );
}
