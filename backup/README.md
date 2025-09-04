{% extends "base.html" %}

{% block title %}Register - SaaS ERP{% endblock %}

{% block content %}
<div class="container-fluid">
    <div class="row justify-content-center">
        <div class="col-lg-8 col-xl-6">
            <div class="card shadow-lg border-0">
                <div class="card-header bg-primary text-white text-center py-4">
                    <h2 class="mb-0">
                        <i class="bi bi-building me-3"></i>Create Your Company Account
                    </h2>
                    <p class="mb-0 mt-2 opacity-75">Start your journey with our powerful SaaS ERP solution</p>
                </div>
                
                <div class="card-body p-5">
                    <form id="registrationForm" method="POST" class="needs-validation" novalidate>
                        <!-- Company Information -->
                        <div class="mb-4">
                            <h5 class="text-primary mb-3">
                                <i class="bi bi-building me-2"></i>Company Information
                            </h5>
                            <div class="row g-3">
                                <div class="col-md-6">
                                    <label for="company_name" class="form-label">Company Name *</label>
                                    <input type="text" class="form-control" id="company_name" name="company_name" 
                                           required placeholder="Enter your company name">
                                    <div class="invalid-feedback">
                                        Please provide a company name.
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <label for="company_website" class="form-label">Website</label>
                                    <input type="url" class="form-control" id="company_website" name="company_website" 
                                           placeholder="https://yourcompany.com">
                                    <div class="invalid-feedback">
                                        Please provide a valid website URL.
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <label for="company_phone" class="form-label">Phone Number</label>
                                    <input type="tel" class="form-control" id="company_phone" name="company_phone" 
                                           placeholder="+1 (555) 123-4567">
                                </div>
                                <div class="col-md-6">
                                    <label for="company_size" class="form-label">Company Size</label>
                                    <select class="form-select" id="company_size" name="company_size">
                                        <option value="">Select company size</option>
                                        <option value="1-10">1-10 employees</option>
                                        <option value="11-50">11-50 employees</option>
                                        <option value="51-200">51-200 employees</option>
                                        <option value="201-500">201-500 employees</option>
                                        <option value="500+">500+ employees</option>
                                    </select>
                                </div>
                                <div class="col-12">
                                    <label for="company_address" class="form-label">Address</label>
                                    <textarea class="form-control" id="company_address" name="company_address" 
                                              rows="2" placeholder="Enter your company address"></textarea>
                                </div>
                                <div class="col-md-6">
                                    <label for="company_city" class="form-label">City</label>
                                    <input type="text" class="form-control" id="company_city" name="company_city" 
                                           placeholder="Enter city">
                                </div>
                                <div class="col-md-3">
                                    <label for="company_state" class="form-label">State/Province</label>
                                    <input type="text" class="form-control" id="company_state" name="company_state" 
                                           placeholder="State">
                                </div>
                                <div class="col-md-3">
                                    <label for="company_zip" class="form-label">ZIP/Postal Code</label>
                                    <input type="text" class="form-control" id="company_zip" name="company_zip" 
                                           placeholder="ZIP">
                                </div>
                                <div class="col-md-6">
                                    <label for="company_country" class="form-label">Country</label>
                                    <select class="form-select" id="company_country" name="company_country">
                                        <option value="">Select country</option>
                                        <option value="US">United States</option>
                                        <option value="CA">Canada</option>
                                        <option value="GB">United Kingdom</option>
                                        <option value="DE">Germany</option>
                                        <option value="FR">France</option>
                                        <option value="IN">India</option>
                                        <option value="AU">Australia</option>
                                        <option value="JP">Japan</option>
                                        <option value="CN">China</option>
                                        <option value="BR">Brazil</option>
                                        <option value="MX">Mexico</option>
                                        <option value="SG">Singapore</option>
                                        <option value="AE">United Arab Emirates</option>
                                        <option value="SA">Saudi Arabia</option>
                                        <option value="ZA">South Africa</option>
                                    </select>
                                </div>
                                <div class="col-md-6">
                                    <label for="company_industry" class="form-label">Industry</label>
                                    <select class="form-select" id="company_industry" name="company_industry">
                                        <option value="">Select industry</option>
                                        <option value="technology">Technology</option>
                                        <option value="healthcare">Healthcare</option>
                                        <option value="finance">Finance</option>
                                        <option value="retail">Retail</option>
                                        <option value="manufacturing">Manufacturing</option>
                                        <option value="education">Education</option>
                                        <option value="real_estate">Real Estate</option>
                                        <option value="consulting">Consulting</option>
                                        <option value="marketing">Marketing</option>
                                        <option value="logistics">Logistics</option>
                                        <option value="other">Other</option>
                                    </select>
                                </div>
                            </div>
                        </div>

                        <!-- Admin User Information -->
                        <div class="mb-4">
                            <h5 class=