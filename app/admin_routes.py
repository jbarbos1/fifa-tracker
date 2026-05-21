from flask import Blueprint, render_template, request, redirect, url_for, flash, session

admin = Blueprint('admin', __name__)


@admin.route('/')
def admin_home():
    return render_template('admin.html')


@admin.route('/dashboard')
def admin_dashboard():
    return render_template('ronin_dashboard.html')
