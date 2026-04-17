import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { 
  AlertTriangle, 
  CheckCircle, 
  XCircle, 
  AlertCircle, 
  TrendingUp, 
  TrendingDown,
  Loader2,
  Activity
} from "lucide-react";
import { useCampaignHealth } from "@/hooks/useApi";
import { CampaignHealthMetric, HealthIssue, SuggestedAction } from "@/types";

interface CampaignHealthProps {
  campaignId: string;
  campaignName?: string;
}

export const CampaignHealth = ({ campaignId, campaignName }: CampaignHealthProps) => {
  const { data: health, isLoading, error } = useCampaignHealth(campaignId);

  const getRiskLevelColor = (riskLevel: CampaignHealthMetric['risk_level']): string => {
    switch (riskLevel) {
      case 'low':
        return 'bg-green-100 text-green-700 border-green-200';
      case 'medium':
        return 'bg-yellow-100 text-yellow-700 border-yellow-200';
      case 'high':
        return 'bg-orange-100 text-orange-700 border-orange-200';
      case 'critical':
        return 'bg-red-100 text-red-700 border-red-200';
      default:
        return 'bg-gray-100 text-gray-700 border-gray-200';
    }
  };

  const getRiskLevelIcon = (riskLevel: CampaignHealthMetric['risk_level']) => {
    switch (riskLevel) {
      case 'low':
        return <CheckCircle className="w-4 h-4" />;
      case 'medium':
        return <AlertCircle className="w-4 h-4" />;
      case 'high':
        return <AlertTriangle className="w-4 h-4" />;
      case 'critical':
        return <XCircle className="w-4 h-4" />;
      default:
        return <Activity className="w-4 h-4" />;
    }
  };

  const getHealthScoreColor = (score: number): string => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-yellow-600';
    if (score >= 40) return 'text-orange-600';
    return 'text-red-600';
  };

  const getSeverityIcon = (severity: HealthIssue['severity']) => {
    switch (severity) {
      case 'critical':
        return <XCircle className="w-4 h-4 text-red-500" />;
      case 'high':
        return <AlertTriangle className="w-4 h-4 text-orange-500" />;
      case 'medium':
        return <AlertCircle className="w-4 h-4 text-yellow-500" />;
      case 'low':
        return <CheckCircle className="w-4 h-4 text-blue-500" />;
      default:
        return <Activity className="w-4 h-4 text-gray-500" />;
    }
  };

  if (error) {
    return (
      <Card className="bg-white shadow-sm border border-gray-200">
        <CardContent className="p-6">
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              Failed to load campaign health data. Please try refreshing.
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-white shadow-sm border border-gray-200">
      <CardHeader className="pb-4">
        <CardTitle className="text-lg font-bold text-gray-900 flex items-center">
          <Activity className="w-5 h-5 mr-2 text-orange-500" />
          Campaign Health Monitor
          {campaignName && (
            <span className="text-sm font-normal text-gray-500 ml-2">
              - {campaignName}
            </span>
          )}
        </CardTitle>
      </CardHeader>
      
      <CardContent>
        {isLoading ? (
          <div className="space-y-4">
            <div className="flex items-center space-x-4">
              <div className="w-16 h-16 bg-gray-200 rounded-full animate-pulse"></div>
              <div className="space-y-2">
                <div className="h-4 bg-gray-200 rounded w-24 animate-pulse"></div>
                <div className="h-6 bg-gray-200 rounded w-20 animate-pulse"></div>
              </div>
            </div>
            <div className="space-y-2">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="h-4 bg-gray-200 rounded animate-pulse"></div>
              ))}
            </div>
          </div>
        ) : health ? (
          <div className="space-y-6">
            {/* Health Score Overview */}
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <div className="relative w-16 h-16">
                  <svg className="w-16 h-16 transform -rotate-90" viewBox="0 0 100 100">
                    <circle cx="50" cy="50" r="35" stroke="#e5e7eb" strokeWidth="8" fill="none" />
                    <circle 
                      cx="50" 
                      cy="50" 
                      r="35" 
                      stroke={health.health_score >= 80 ? "#10b981" : 
                             health.health_score >= 60 ? "#f59e0b" : 
                             health.health_score >= 40 ? "#f97316" : "#ef4444"}
                      strokeWidth="8" 
                      fill="none"
                      strokeDasharray="220"
                      strokeDashoffset={220 - (220 * health.health_score / 100)}
                      className="transition-all duration-300"
                    />
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className={`text-lg font-bold ${getHealthScoreColor(health.health_score)}`}>
                      {health.health_score.toFixed(0)}
                    </span>
                  </div>
                </div>
                
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">Health Score</h3>
                  <div className="flex items-center space-x-2">
                    <Badge className={`text-xs px-3 py-1 rounded-full border font-semibold ${getRiskLevelColor(health.risk_level)}`}>
                      {getRiskLevelIcon(health.risk_level)}
                      <span className="ml-1">{health.risk_level.toUpperCase()} RISK</span>
                    </Badge>
                  </div>
                </div>
              </div>
              
              <div className="text-right">
                <p className="text-xs text-gray-500">Last Updated</p>
                <p className="text-sm font-medium text-gray-900">
                  {new Date(health.last_updated).toLocaleDateString()}
                </p>
              </div>
            </div>

            {/* Issues Detected */}
            {health.issues.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center">
                  <AlertTriangle className="w-4 h-4 mr-2 text-orange-500" />
                  Issues Detected ({health.issues.length})
                </h4>
                <div className="space-y-2">
                  {health.issues.map((issue, index) => (
                    <div key={index} className="flex items-start space-x-3 p-3 bg-gray-50 rounded-lg">
                      {getSeverityIcon(issue.severity)}
                      <div className="flex-1">
                        <p className="text-sm font-medium text-gray-900 capitalize">
                          {issue.type.replace('_', ' ')}
                        </p>
                        <p className="text-xs text-gray-600 mt-1">
                          {issue.message}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Suggested Actions */}
            {health.suggested_actions.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center">
                  <TrendingUp className="w-4 h-4 mr-2 text-blue-500" />
                  Suggested Actions ({health.suggested_actions.length})
                </h4>
                <div className="space-y-2">
                  {health.suggested_actions.map((action, index) => (
                    <div key={index} className="flex items-start space-x-3 p-3 bg-blue-50 rounded-lg">
                      <CheckCircle className="w-4 h-4 text-blue-500 mt-0.5" />
                      <div className="flex-1">
                        <p className="text-sm font-medium text-gray-900 capitalize">
                          {action.action.replace('_', ' ')}
                        </p>
                        <p className="text-xs text-gray-600 mt-1">
                          {action.message}
                        </p>
                      </div>
                      <Button 
                        size="sm" 
                        variant="outline" 
                        className="text-xs border-blue-200 text-blue-600 hover:bg-blue-100"
                        onClick={() => {
                          // In a real app, this would trigger the suggested action
                          alert(`Action: ${action.action}\n\n${action.message}`);
                        }}
                      >
                        Apply
                      </Button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* No Issues */}
            {health.issues.length === 0 && (
              <div className="text-center py-6">
                <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-3" />
                <h3 className="text-lg font-semibold text-gray-900 mb-1">Campaign is Healthy</h3>
                <p className="text-sm text-gray-600">
                  No critical issues detected. Campaign is performing within expected parameters.
                </p>
              </div>
            )}
          </div>
        ) : (
          <div className="text-center py-6 text-gray-500">
            <Activity className="w-8 h-8 mx-auto mb-2" />
            <p className="text-sm">No health data available for this campaign.</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
