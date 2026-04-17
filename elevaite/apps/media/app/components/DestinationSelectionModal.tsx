"use client";
import { CommonButton, ElevaiteIcons, ChatbotIcons } from "@repo/ui/components";
import { IODestination, type DestinationSelectionModalProps } from "../lib/interfaces";
import "./DestinationSelectionModal.scss";

export function DestinationSelectionModal({ isOpen, onClose, onDestinationSelect }: DestinationSelectionModalProps): JSX.Element | null {
  if (!isOpen) return null;

  const handleDestinationSelect = (destination: IODestination) => {
    onDestinationSelect(destination);
    onClose();
  };

  return (
    <div className="destination-selection-modal">
      {/* Header */}
      <div className="destination-selection-header">
        <span className="destination-selection-header__icon">
          <ElevaiteIcons.SVGRegister />
        </span>
        <span className="destination-selection-header__title">Generate Insertion Order</span>
        <button className="destination-selection-header__close" onClick={onClose} aria-label="Close">
          <ElevaiteIcons.SVGXmark/>
        </button>
      </div>

      {/* Content */}
      <div className="destination-selection-content">
        <p className="destination-selection-subtitle">Choose where to send your generated insertion order</p>
        
        <div className="destination-options">
          {/* Google Drive/Sheets Option */}
          <div 
            className="destination-card destination-card--enabled"
            onClick={() => handleDestinationSelect(IODestination.GOOGLE_WORKSPACE)}
          >
            <div className="destination-card__icon destination-card__icon--google">
              <ChatbotIcons.SVGDocument />
            </div>
            <div className="destination-card__content">
              <h3 className="destination-card__title">Google Workspace</h3>
              <p className="destination-card__description">Export insertion order to Google Sheets and Drive</p>
              <div className="destination-card__features">
                <div className="feature-item">
                  <ElevaiteIcons.SVGCheckmark className="feature-icon" />
                  <span>Direct spreadsheet export</span>
                </div>
                <div className="feature-item">
                  <ElevaiteIcons.SVGCheckmark className="feature-icon" />
                  <span>PDF document generation</span>
                </div>
                <div className="feature-item">
                  <ElevaiteIcons.SVGCheckmark className="feature-icon" />
                  <span>Organized folder structure</span>
                </div>
              </div>
            </div>
            <div className="destination-card__action">
              <CommonButton className="destination-card__button">
                Export to Google Workspace
                <ElevaiteIcons.SVGChevron type="right" />
              </CommonButton>
            </div>
          </div>

          {/* Salesforce Option */}
          <div
            className="destination-card destination-card--enabled"
            onClick={() => handleDestinationSelect(IODestination.SALESFORCE)}
          >
            <div className="destination-card__icon destination-card__icon--salesforce">
              <ElevaiteIcons.SVGDatasets />
            </div>
            <div className="destination-card__content">
              <h3 className="destination-card__title">Salesforce</h3>
              <p className="destination-card__description">Export insertion order to Salesforce CRM</p>
              <div className="destination-card__features">
                <div className="feature-item">
                  <ElevaiteIcons.SVGCheckmark className="feature-icon" />
                  <span>CRM integration</span>
                </div>
                <div className="feature-item">
                  <ElevaiteIcons.SVGCheckmark className="feature-icon" />
                  <span>Opportunity linking</span>
                </div>
                <div className="feature-item">
                  <ElevaiteIcons.SVGCheckmark className="feature-icon" />
                  <span>Automated workflows</span>
                </div>
              </div>
            </div>
            <div className="destination-card__action">
              <CommonButton className="destination-card__button">
                Export to Salesforce
                <ElevaiteIcons.SVGChevron type="right" />
              </CommonButton>
            </div>
          </div>
        </div>

        <p className="destination-selection-footer">Choose your preferred destination to continue with IO generation</p>
      </div>
    </div>
  );
}
