import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Calendar } from "@/components/ui/calendar";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Clock, MapPin, Users } from "lucide-react";

interface CalendarEvent {
  id: string;
  summary: string;
  start: {
    dateTime?: string;
    date?: string;
  };
  end: {
    dateTime?: string;
    date?: string;
  };
  location?: string;
  attendees?: Array<{ email: string; displayName?: string }>;
  description?: string;
}

interface GoogleCalendarViewProps {
  isConnected: boolean;
  email?: string; // ← NEW: pass the authorized email from MainApp
}

export const GoogleCalendarView = ({ isConnected, email }: GoogleCalendarViewProps) => {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [selectedDate, setSelectedDate] = useState<Date>(new Date());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchCalendarEvents = async (date: Date) => {
    if (!isConnected) return;

    setLoading(true);
    setError(null);

    try {
      // Keep your Sunday-start week logic
      const startOfWeek = new Date(date);
      startOfWeek.setDate(date.getDate() - date.getDay());

      const endOfWeek = new Date(startOfWeek);
      endOfWeek.setDate(startOfWeek.getDate() + 7);

      // Build query string; include email if provided
      const qs =
        `?${email ? `email=${encodeURIComponent(email)}&` : ""}` +
        `start=${encodeURIComponent(startOfWeek.toISOString())}` +
        `&end=${encodeURIComponent(endOfWeek.toISOString())}`;

      const response = await fetch(`/api/calendar/events${qs}`);

      if (!response.ok) {
        throw new Error("Failed to fetch calendar events");
      }

      const data = await response.json();

      // Normalize to Google-like shape in case backend returns flat start/end
      const normalized: CalendarEvent[] = (data.events || []).map((e: any, idx: number) => ({
        id: e.id ?? e.eventId ?? String(idx),
        summary: e.summary ?? "(no title)",
        start:
          e.start?.dateTime || e.start?.date
            ? e.start
            : e.start
              ? { dateTime: e.start }
              : {},
        end:
          e.end?.dateTime || e.end?.date
            ? e.end
            : e.end
              ? { dateTime: e.end }
              : {},
        location: e.location,
        attendees: e.attendees || [],
        description: e.description,
      }));

      setEvents(normalized);
    } catch (err) {
      console.error("Calendar fetch error:", err);
      setError("Network error while fetching events");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isConnected) {
      fetchCalendarEvents(selectedDate);
    }
    // re-fetch when email changes too
  }, [isConnected, selectedDate, email]);

  const formatEventTime = (event: CalendarEvent) => {
    if (event.start?.dateTime && event.end?.dateTime) {
      const startTime = new Date(event.start.dateTime);
      const endTime = new Date(event.end.dateTime);
      return `${startTime.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} - ${endTime.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
    }
    return "All day";
  };

  const getEventsForSelectedDate = () => {
    return events.filter((event) => {
      const startStr = event.start?.dateTime || event.start?.date;
      if (!startStr) return false;
      const eventDate = new Date(startStr);
      return eventDate.toDateString() === selectedDate.toDateString();
    });
  };

  const todaysEvents = getEventsForSelectedDate();

  return (
    <div className="h-full flex flex-col space-y-4">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 flex-1">
        {/* Calendar */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm text-muted-foreground">Calendar</CardTitle>
          </CardHeader>
          <CardContent>
            <Calendar
              mode="single"
              selected={selectedDate}
              onSelect={(date) => date && setSelectedDate(date)}
              className="rounded-md border w-full"
            />
          </CardContent>
        </Card>

        {/* Events for selected date */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm text-muted-foreground">
              Events for {selectedDate.toLocaleDateString()}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[300px]">
              {loading ? (
                <div className="flex items-center justify-center py-8">
                  <div className="text-sm text-muted-foreground">Loading events...</div>
                </div>
              ) : error ? (
                <div className="flex items-center justify-center py-8">
                  <div className="text-sm text-destructive">{error}</div>
                </div>
              ) : todaysEvents.length === 0 ? (
                <div className="flex items-center justify-center py-8">
                  <div className="text-sm text-muted-foreground">No events for this day</div>
                </div>
              ) : (
                <div className="space-y-3">
                  {todaysEvents.map((event) => (
                    <div
                      key={event.id}
                      className="p-3 rounded-lg border bg-card hover:bg-accent/50 transition-colors"
                    >
                      <div className="flex items-start justify-between mb-2">
                        <h4 className="font-medium text-sm line-clamp-2">{event.summary}</h4>
                        <Badge variant="outline" className="ml-2 text-xs">
                          {event.start?.dateTime ? "Meeting" : "All day"}
                        </Badge>
                      </div>

                      <div className="flex items-center gap-4 text-xs text-muted-foreground">
                        <div className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {formatEventTime(event)}
                        </div>

                        {event.location && (
                          <div className="flex items-center gap-1">
                            <MapPin className="w-3 h-3" />
                            <span className="truncate max-w-[120px]">{event.location}</span>
                          </div>
                        )}

                        {event.attendees && event.attendees.length > 0 && (
                          <div className="flex items-center gap-1">
                            <Users className="w-3 h-3" />
                            <span>{event.attendees.length}</span>
                          </div>
                        )}
                      </div>

                      {event.description && (
                        <p className="text-xs text-muted-foreground mt-2 line-clamp-2">
                          {event.description}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </ScrollArea>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
