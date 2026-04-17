
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ChevronRight, Loader2, AlertCircle, CheckCircle2, MoreVertical, Eye, X } from "lucide-react";
import { useTasks, useUpdateTaskStatus } from "@/hooks/useApi";
import { Task } from "@/types";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { useState } from "react";

export const TaskList = () => {
  const { data: tasks, isLoading, error } = useTasks();
  const updateTaskStatus = useUpdateTaskStatus();
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);

  const getPriorityColor = (priority: Task['priority']): string => {
    switch (priority) {
      case 'high':
        return 'bg-red-100 text-red-700 border-red-200 hover:bg-red-100 hover:text-red-700 hover:border-red-200';
      case 'medium':
        return 'bg-orange-100 text-orange-700 border-orange-200 hover:bg-orange-100 hover:text-orange-700 hover:border-orange-200';
      case 'low':
        return 'bg-blue-100 text-blue-700 border-blue-200 hover:bg-blue-100 hover:text-blue-700 hover:border-blue-200';
      default:
        return 'bg-gray-100 text-gray-700 border-gray-200 hover:bg-gray-100 hover:text-gray-700 hover:border-gray-200';
    }
  };

  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: '2-digit',
      day: '2-digit',
      year: 'numeric'
    });
  };

  const handleTaskComplete = async (taskId: string) => {
    try {
      await updateTaskStatus.mutateAsync({ id: taskId, status: 'completed' });
    } catch (error) {
      console.error('Failed to update task status:', error);
    }
  };

  const handleTaskDismiss = async (taskId: string) => {
    try {
      await updateTaskStatus.mutateAsync({ id: taskId, status: 'dismissed' });
    } catch (error) {
      console.error('Failed to dismiss task:', error);
    }
  };

  const handleViewTask = (task: Task) => {
    setSelectedTask(task);
    // TODO: Open task details modal
    alert(`Task Details:\n\nTitle: ${task.title}\nDescription: ${task.description || 'No description'}\nAssigned to: ${task.assigned_to || 'Unassigned'}\nDue: ${formatDate(task.due_date)}`);
  };

  // Filter to show only pending and in_progress tasks, sorted by priority (high first) then by due date
  const activeTasks = tasks?.filter(task => task.status !== 'completed' && task.status !== 'dismissed')
    .sort((a, b) => {
      // Priority order: high = 1, medium = 2, low = 3
      const priorityOrder = { high: 1, medium: 2, low: 3 };
      const aPriority = priorityOrder[a.priority as keyof typeof priorityOrder] || 4;
      const bPriority = priorityOrder[b.priority as keyof typeof priorityOrder] || 4;

      if (aPriority !== bPriority) {
        return aPriority - bPriority;
      }

      // If same priority, sort by due date
      return new Date(a.due_date).getTime() - new Date(b.due_date).getTime();
    }) || [];

  if (error) {
    return (
      <Card className="bg-white shadow-sm border border-gray-200 h-fit">
        <CardContent className="p-6">
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              Failed to load tasks. Please try refreshing.
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-white shadow-sm border border-gray-200 h-full flex flex-col overflow-hidden">
      <CardHeader className="bg-gray-50 px-6 py-4 flex-shrink-0 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium text-gray-600 uppercase tracking-wide">Tasks To-Do</CardTitle>
          <div className="flex items-center space-x-8 text-xs font-medium text-gray-500 uppercase tracking-wide">
            <span>Priority</span>
            <span>Due</span>
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-0 flex-1 flex flex-col">
        {isLoading ? (
          <div className="flex-1 px-6 divide-y divide-gray-100">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="flex items-center justify-between py-4">
                <div className="flex-1 pr-4">
                  <div className="h-4 bg-gray-200 rounded w-3/4 animate-pulse"></div>
                </div>
                <div className="flex items-center space-x-4">
                  <div className="h-6 bg-gray-200 rounded-full w-16 animate-pulse"></div>
                  <div className="h-4 bg-gray-200 rounded w-20 animate-pulse"></div>
                  <div className="h-6 w-6 bg-gray-200 rounded animate-pulse"></div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="flex-1 flex flex-col">
            {activeTasks.length > 0 ? (
              <div className="divide-y divide-gray-100">
                {activeTasks.slice(0, 5).map((task) => (
                  <div key={task.id} className="flex items-center justify-between py-4 px-6 group">
                    <div className="flex-1 min-w-0 pr-4">
                      <p className="text-sm text-gray-700 leading-relaxed">
                        {task.title}
                      </p>
                    </div>
                    <div className="flex items-center space-x-4">
                      <Badge className={`text-xs px-3 py-1 rounded-full border font-medium ${getPriorityColor(task.priority)}`}>
                        {task.priority.charAt(0).toUpperCase() + task.priority.slice(1)}
                      </Badge>
                      <span className="text-xs text-gray-500 whitespace-nowrap font-medium min-w-[80px] text-right">
                        {formatDate(task.due_date)}
                      </span>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-6 w-6 p-0 hover:bg-gray-100 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
                            disabled={updateTaskStatus.isPending}
                          >
                            {updateTaskStatus.isPending ? (
                              <Loader2 className="h-3 w-3 animate-spin text-gray-400" />
                            ) : (
                              <MoreVertical className="h-3 w-3 text-gray-400" />
                            )}
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="w-48">
                          <DropdownMenuItem onClick={() => handleTaskComplete(task.id)}>
                            <CheckCircle2 className="h-4 w-4 mr-2 text-green-600" />
                            Mark Completed
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => handleViewTask(task)}>
                            <Eye className="h-4 w-4 mr-2 text-blue-600" />
                            View Task
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => handleTaskDismiss(task.id)}>
                            <X className="h-4 w-4 mr-2 text-red-600" />
                            Dismiss
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center text-gray-500 py-12 px-6">
                <CheckCircle2 className="h-8 w-8 mx-auto mb-2 text-green-500" />
                <p className="text-sm">All tasks completed!</p>
              </div>
            )}
          </div>
        )}

        <div className="px-6 py-4 border-t border-gray-100 flex-shrink-0">
          <Button
            variant="ghost"
            className="w-full text-orange-500 hover:text-orange-600 text-sm font-medium justify-center"
            onClick={() => {
              // In a real app, this would navigate to a full tasks page
              alert('Full tasks view would be implemented here');
            }}
          >
            view all tasks →
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};
