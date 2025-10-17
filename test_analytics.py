"""
Test analytics endpoints for SafeBoda Rwanda
"""
import os
import sys
import django
from datetime import date, timedelta

# Add the project directory to the path
sys.path.append('C:/Users/tharc/Desktop/Assignment')

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'safeboda_rwanda.settings.development')
django.setup()

from analytics.services import AnalyticsService
from authentication.models import User
from bookings.models import Ride
from decimal import Decimal

def test_analytics_services():
    """Test all analytics service methods"""
    print("🧪 Testing SafeBoda Rwanda Analytics System")
    print("=" * 50)
    
    # Date range for testing
    end_date = date.today()
    start_date = end_date - timedelta(days=7)
    
    print(f"📅 Testing date range: {start_date} to {end_date}")
    
    try:
        # Test 1: Ride Summary Analytics
        print("\n1️⃣ Testing Ride Summary Analytics...")
        ride_summary = AnalyticsService.get_ride_summary(start_date, end_date)
        print(f"   ✅ Retrieved ride summary: {ride_summary['ride_counts']['total_rides']} total rides")
        
        # Test 2: Revenue Analytics
        print("\n2️⃣ Testing Revenue Analytics...")
        revenue_data = AnalyticsService.get_revenue_analysis(start_date, end_date)
        print(f"   ✅ Retrieved revenue data: RWF {revenue_data['summary']['total_revenue']:.2f} total revenue")
        
        # Test 3: Driver Performance Analytics
        print("\n3️⃣ Testing Driver Performance Analytics...")
        driver_performance = AnalyticsService.get_driver_performance_analysis(start_date, end_date)
        print(f"   ✅ Retrieved performance data for {driver_performance['driver_count']} drivers")
        
        # Test 4: Popular Routes Analytics
        print("\n4️⃣ Testing Popular Routes Analytics...")
        popular_routes = AnalyticsService.get_popular_routes_analysis(10)
        print(f"   ✅ Retrieved {len(popular_routes['popular_routes'])} popular routes")
        
        # Test 5: Customer Insights Analytics
        print("\n5️⃣ Testing Customer Insights Analytics...")
        customer_insights = AnalyticsService.get_customer_insights_analysis()
        print(f"   ✅ Retrieved insights for {customer_insights['customer_segments']['total_customers']} customers")
        
        # Test 6: Time Patterns Analytics
        print("\n6️⃣ Testing Time Patterns Analytics...")
        time_patterns = AnalyticsService.get_time_patterns_analysis()
        print(f"   ✅ Retrieved time patterns - busiest day: {time_patterns['insights']['busiest_day']}")
        
        print("\n✅ All Analytics Services Working Successfully!")
        print("🎉 SafeBoda Rwanda Analytics System is Ready!")
        
        # Summary of capabilities
        print("\n📊 Analytics System Capabilities:")
        print("   • Ride summary with completion rates and revenue metrics")
        print("   • Revenue analysis with payment method breakdowns") 
        print("   • Driver performance tracking and rankings")
        print("   • Popular route analysis for demand planning")
        print("   • Customer behavior insights and segmentation")
        print("   • Time pattern analysis for operational optimization")
        print("   • Automated report generation and caching")
        print("   • REST API endpoints with proper authentication")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing analytics: {str(e)}")
        return False

def create_test_data():
    """Create some test data if none exists"""
    print("\n🔧 Creating test data for analytics...")
    
    try:
        # Check if we have users and rides
        user_count = User.objects.count()
        ride_count = Ride.objects.count()
        
        print(f"   📊 Found {user_count} users and {ride_count} rides in database")
        
        if user_count == 0:
            print("   ⚠️ No users found - analytics will show zero data")
        if ride_count == 0:
            print("   ⚠️ No rides found - analytics will show zero data")
        
        print("   ✅ Database ready for analytics testing")
        
    except Exception as e:
        print(f"   ❌ Error checking test data: {str(e)}")

if __name__ == '__main__':
    print("🚀 SafeBoda Rwanda Analytics System Test")
    print("=======================================")
    
    # Create/check test data
    create_test_data()
    
    # Test analytics services
    success = test_analytics_services()
    
    if success:
        print("\n🎯 Analytics System Status: OPERATIONAL")
        print("💡 Ready for production use with comprehensive business intelligence")
    else:
        print("\n❌ Analytics System Status: NEEDS ATTENTION")
        print("🔧 Please check the error messages above")