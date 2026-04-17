"use client";
import { useState, useRef, useEffect } from "react";
import { CommonButton, ElevaiteIcons, type CommonSelectOption } from "@repo/ui/components";
import "./SearchableSelect.scss";

export interface SearchableSelectProps {
  options: CommonSelectOption[];
  value?: string;
  onValueChange: (value: string, label: string) => void;
  placeholder?: string;
  disabled?: boolean;
  isLoading?: boolean;
  searchPlaceholder?: string;
  noResultsMessage?: string;
  searchFields?: (option: CommonSelectOption) => string[]; // Custom function to define what fields to search
}

export function SearchableSelect({
  options,
  value,
  onValueChange,
  placeholder = "Select an option",
  disabled = false,
  isLoading = false,
  searchPlaceholder = "Type to search...",
  noResultsMessage = "No results found",
  searchFields
}: SearchableSelectProps): JSX.Element {
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [filteredOptions, setFilteredOptions] = useState<CommonSelectOption[]>(options);
  const [selectedOption, setSelectedOption] = useState<CommonSelectOption | undefined>();
  
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Find selected option when value changes
  useEffect(() => {
    const found = options.find(option => option.value === value);
    setSelectedOption(found);
  }, [value, options]);

  // Filter options based on search term
  useEffect(() => {
    if (!searchTerm) {
      setFilteredOptions(options);
    } else {
      const filtered = options.filter(option => {
        const searchLower = searchTerm.toLowerCase();
        
        if (searchFields) {
          // Use custom search fields function
          const fieldsToSearch = searchFields(option);
          return fieldsToSearch.some(field => 
            field.toLowerCase().includes(searchLower)
          );
        } else {
          // Default search: label and value
          const labelMatch = option.label?.toLowerCase().includes(searchLower);
          const valueMatch = option.value.toLowerCase().includes(searchLower);
          return labelMatch || valueMatch;
        }
      });
      setFilteredOptions(filtered);
    }
  }, [searchTerm, options, searchFields]);

  // Handle click outside to close dropdown
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
        setSearchTerm("");
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isOpen]);

  const handleToggle = () => {
    if (disabled || isLoading) return;
    
    setIsOpen(!isOpen);
    if (!isOpen) {
      // Focus input when opening
      setTimeout(() => inputRef.current?.focus(), 0);
    } else {
      // Clear search when closing
      setSearchTerm("");
    }
  };

  const handleOptionClick = (option: CommonSelectOption) => {
    setSelectedOption(option);
    onValueChange(option.value, option.label || option.value);
    setIsOpen(false);
    setSearchTerm("");
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(e.target.value);
  };

  const handleInputKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Escape') {
      setIsOpen(false);
      setSearchTerm("");
    } else if (e.key === 'Enter' && filteredOptions.length > 0) {
      handleOptionClick(filteredOptions[0]);
    }
  };

  return (
    <div 
      ref={containerRef}
      className={`searchable-select ${disabled ? 'disabled' : ''} ${isOpen ? 'open' : ''}`}
    >
      <div className="searchable-select__trigger" onClick={handleToggle}>
        <span className="searchable-select__value">
          {isLoading ? "Loading..." : 
           selectedOption ? (selectedOption.label || selectedOption.value) : 
           placeholder}
        </span>
        {isLoading ? (
          <ElevaiteIcons.SVGSpinner className="searchable-select__spinner" />
        ) : (
          <ElevaiteIcons.SVGChevron 
            className={`searchable-select__chevron ${isOpen ? 'open' : ''}`} 
            type="down" 
          />
        )}
      </div>

      {isOpen && (
        <div ref={dropdownRef} className="searchable-select__dropdown">
          <div className="searchable-select__search">
            <input
              ref={inputRef}
              type="text"
              value={searchTerm}
              onChange={handleInputChange}
              onKeyDown={handleInputKeyDown}
              placeholder={searchPlaceholder}
              className="searchable-select__search-input"
            />
            <ElevaiteIcons.SVGMagnifyingGlass className="searchable-select__search-icon" />
          </div>
          
          <div className="searchable-select__options">
            {filteredOptions.length === 0 ? (
              <div className="searchable-select__no-results">
                {noResultsMessage}
              </div>
            ) : (
              filteredOptions.map((option) => (
                <CommonButton
                  key={option.value}
                  className={`searchable-select__option ${
                    selectedOption?.value === option.value ? 'selected' : ''
                  }`}
                  onClick={() => handleOptionClick(option)}
                  noBackground
                  disabled={option.disabled}
                >
                  <div className="searchable-select__option-content">
                    <span className="searchable-select__option-label">
                      {option.label || option.value}
                    </span>
                    {option.extras?.postfix && (
                      <span className="searchable-select__option-description">
                        {option.extras.postfix.label}
                      </span>
                    )}
                  </div>
                  {selectedOption?.value === option.value && (
                    <ElevaiteIcons.SVGCheckmark className="searchable-select__checkmark" />
                  )}
                </CommonButton>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
