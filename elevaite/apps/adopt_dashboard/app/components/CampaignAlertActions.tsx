"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertTriangle, Lightbulb } from "lucide-react";

interface CampaignAlertActionsProps {
  campaignId?: string;
  campaignName?: string;
  campaign?: any; // Add campaign object to access dates
}

export default function CampaignAlertActions({ campaignId, campaignName, campaign }: CampaignAlertActionsProps) {
  // Check if campaign is completed
  const isCompleted = campaign?.end_date ? new Date(campaign.end_date) < new Date() : false;

  // Temporary placeholder content until real alert/suggestion logic is wired up
  const items = isCompleted
    ? [
        {
          alert: "Campaign completed; review performance and document learnings.",
          action: "Export final report and archive creatives.",
        },
        {
          alert: "Pacing ended; ensure billing reconciliation is complete.",
          action: "Confirm invoices and close insertion orders.",
        },
      ]
    : [
        {
          alert: "CTR trending below target over the last 7 days.",
          action: "Test new creatives and refine targeting.",
        },
        {
          alert: "Pacing behind weekly budget allocation.",
          action: "Increase daily budget or extend flight dates.",
        },
        {
          alert: "High CPA on mobile inventory.",
          action: "Lower mobile bids or exclude low-performing apps.",
        },
      ];

  return (
    <Card className="bg-white shadow-sm border border-gray-200">
      <CardHeader className="pb-3">
        <div className="flex items-center space-x-2">
          <AlertTriangle className="w-5 h-5 text-yellow-600" />
          <CardTitle className="text-base">
            {isCompleted ? "Campaign Analysis & Insights" : "Alerts & Suggested Actions"}
          </CardTitle>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="divide-y divide-gray-100">
          {items.map((item, idx) => (
            <div key={idx} className="py-3">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-start">
                {/* Left: Alert */}
                <div className="text-sm text-gray-800">
                  <span className="inline-flex items-center rounded-md bg-yellow-50 text-yellow-700 ring-1 ring-yellow-200 px-2 py-0.5 mr-2 text-xs">Alert</span>
                  {item.alert}
                </div>
                {/* Right: Suggested action */}
                <div className="text-sm text-gray-700 md:text-right">
                  <div className="inline-flex items-center gap-2">
                    <Lightbulb className="w-4 h-4 text-emerald-500" />
                    <span className="text-gray-800">{item.action}</span>
                    <button className="cursor-default rounded border border-gray-200 text-gray-400 text-xs px-2 py-1" disabled>
                      Placeholder
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
