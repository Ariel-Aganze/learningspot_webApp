# Add this to your main project's views.py or create a new views.py file in your main project directory

from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings

def home_view(request):
    """Home page view with contact form handling"""
    if request.method == 'POST':
        # Get form data
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        email = request.POST.get('email', '')
        phone = request.POST.get('phone', '')
        subject = request.POST.get('subject', '')
        message = request.POST.get('message', '')
        consent = request.POST.get('consent', '')
        
        # Basic validation
        if not all([first_name, last_name, email, subject, message, consent]):
            messages.error(request, 'Please fill in all required fields and agree to be contacted.')
            return render(request, 'home.html')
        
        try:
            # Prepare email content
            email_subject = f"Contact Form: {dict(request.POST.lists()).get('subject', [''])[0].replace('_', ' ').title()}"
            email_message = f"""
New contact form submission from Learning Spot website:

Name: {first_name} {last_name}
Email: {email}
Phone: {phone if phone else 'Not provided'}
Subject: {subject.replace('_', ' ').title()}

Message:
{message}

---
This message was sent from the Learning Spot contact form.
            """
            
            # Send email
            send_mail(
                subject=email_subject,
                message=email_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.DEFAULT_FROM_EMAIL],  # Send to yourself
                fail_silently=False,
            )
            
            # Success message
            messages.success(request, 'Thank you for your message! We\'ll get back to you within 24 hours.')
            return redirect('home')
            
        except Exception as e:
            # Error handling
            messages.error(request, 'Sorry, there was an error sending your message. Please try again or contact us directly.')
            return render(request, 'home.html')
    
    # GET request - just show the page
    return render(request, 'home.html')