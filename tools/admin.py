import model

def recent_reports(count=100):
    return model.Report.all().order('-arrived').fetch(count)

def show_recent_reports(count=100):
    for report in reversed(recent_reports(count)):
        changes = []
        for property in report.dynamic_properties():
            if property.endswith('__'):
                changes.append('%s = %s' % (
                    property.rstrip('_'), getattr(report, property)))
        print ('%s (%s): %s - %s' % (
            report.observed, report.author.email(),
            report.parent_key().name(), ', '.join(changes))).encode('utf-8')
