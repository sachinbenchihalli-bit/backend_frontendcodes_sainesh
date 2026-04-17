import React from 'react';
import { RelatedQueriesDisplayProps } from '../lib/interfaces';
import './RelatedQueriesDisplay.scss';
import  SVGMagnifyingGlass  from '../../../../packages/ui/src/components/icons/elevaite/svgMagnifyingGlass'



const RelatedQueriesDisplay: React.FC<RelatedQueriesDisplayProps> = ({ queries, onQueryClick, onGenerateIOClick }) => {

    const handleQueryClick = (query: string) => {
        // Normalize strings for flexible comparison (remove punctuation, lowercase, trim)
        const normalizeString = (str: string) =>
            str.toLowerCase().replace(/[^\w\s]/g, '').trim();

        const normalizedQuery = normalizeString(query);
        const targetQuery = normalizeString("Create an Insertion Order(IO) from the Media Plan");

        // Check if this is the specific IO query with flexible matching
        if (normalizedQuery === targetQuery && onGenerateIOClick) {
            onGenerateIOClick();
        } else {
            onQueryClick(query);
        }
    };

    return (
        <div className="related-queries-container">
            <h4>Related:</h4>
            <ul>
                {queries.map((query, index) => (
                    <div key={index} onClick={() => handleQueryClick(query)} className="query-item">
                        <span className="query-text">{query}</span>
                        <SVGMagnifyingGlass className="query-icon"/>
                    </div>
                ))}
            </ul>
        </div>
    );
};
export default RelatedQueriesDisplay;