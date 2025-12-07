CREATE OR REPLACE  FUNCTION notify_new_request()
RETURNS TRIGGER AS $$
DECLARE 
    payload JSON;
BEGIN
    payload = json_build_object(
        'task_id', NEW.id,
        'priority', NEW.priority,
        'assigned_to', NEW.assign_to 
    );
    PERFORM pg_notify('new_requests_channel', payload::text);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER new_lab_request
AFTER INSERT ON requests
FOR EACH ROW
EXECUTE FUNCTION notify_new_request();