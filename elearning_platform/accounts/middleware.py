# Create a new file: accounts/middleware.py

from django.shortcuts import redirect
from django.contrib import messages
from django.urls import resolve, reverse
from django.utils import timezone

class CourseAccessMiddleware:
    """Middleware to check if a student has access to a course based on their course period"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Only process if user is authenticated and is a student
        if not request.user.is_authenticated or not hasattr(request.user, 'is_student') or not request.user.is_student():
            return self.get_response(request)
        
        # Only check course access for student course dashboard and related pages
        path = request.path_info
        if '/courses/' in path and '/dashboard/' in path:
            try:
                # Get the course slug from the URL
                url_match = resolve(path)
                if 'slug' in url_match.kwargs:
                    course_slug = url_match.kwargs['slug']
                    
                    # Import models here to avoid circular imports
                    from courses.models import Course
                    from accounts.models import CoursePeriod
                    
                    # Get the course
                    course = Course.objects.get(slug=course_slug)
                    
                    # Check if there's a course period for this student and course
                    course_period = CoursePeriod.objects.filter(
                        student=request.user,
                        course=course
                    ).first()
                    
                    # If there's a course period and it's expired, redirect to dashboard
                    if course_period and course_period.is_expired():
                        messages.error(
                            request, 
                            f"Your access to {course.title} has expired on {course_period.end_date.strftime('%B %d, %Y')}. "
                            "Please contact your instructor or administrator if you need an extension."
                        )
                        return redirect('student_dashboard')
                        
            except Exception as e:
                # If any error occurs, just proceed with the request
                pass
        
        return self.get_response(request)
    
class OrganizationSubscriptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Process request before view is called
        if request.user.is_authenticated and hasattr(request.user, 'student_profile'):
            # Check if user is a student with an organization
            profile = request.user.student_profile
            if profile.organization and not profile.organization.is_subscription_active:
                # Only block access to course content, not the entire site
                path = request.path
                # Assuming course content is under /courses/
                if path.startswith('/courses/') and not path.startswith('/courses/placement-test/'):
                    messages.warning(
                        request, 
                        "Your organization's subscription has expired. Please contact your administrator."
                    )
                    return redirect(reverse('student_dashboard'))
        
        response = self.get_response(request)
        return response