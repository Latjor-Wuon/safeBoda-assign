"""
OpenAPI Documentation Configuration for SafeBoda Rwanda Platform
Comprehensive API specification for integrated ride-booking system
"""
from drf_spectacular.openapi import AutoSchema
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.openapi import OpenApiTypes
from drf_spectacular import openapi
from rest_framework import status
import os

# SafeBoda Rwanda OpenAPI Configuration
SPECTACULAR_SETTINGS = {
    'TITLE': 'SafeBoda Rwanda API',
    'DESCRIPTION': '''
    # SafeBoda Rwanda Platform API

    **Complete ride-booking platform API for Rwanda with integrated features:**

    ## 🚀 Platform Features
    - **Real-time ride booking** with live driver tracking
    - **Rwanda mobile money integration** (MTN MoMo, Airtel Money)
    - **Government compliance** reporting and regulatory features
    - **Advanced analytics** with performance insights
    - **WebSocket support** for real-time updates
    - **Async processing** for scalable operations

    ## 🏛️ Regulatory Compliance
    - **BNR (Bank of Rwanda)** financial reporting
    - **RRA (Rwanda Revenue Authority)** tax compliance
    - **RTDA (Rwanda Transport Development Agency)** licensing
    - **Government reporting** with audit trails

    ## 🔐 Authentication
    The API uses **JWT-based authentication** with role-based access control:
    - **Customers**: Ride booking and tracking
    - **Drivers**: Ride management and earnings
    - **Admins**: Platform management and analytics
    - **Government Officials**: Compliance reporting access

    ## 📱 Rwanda-Specific Features
    - **District-based service areas** (Gasabo, Nyarugenge, Kicukiro)
    - **Local payment methods** integration
    - **Kinyarwanda language** support
    - **Local regulations** compliance

    ## 🔄 Real-time Features
    - **WebSocket connections** for live tracking
    - **Push notifications** for ride updates
    - **Live driver positioning** with ETA calculations
    - **Real-time payment processing**

    ## 📊 Analytics & Reporting
    - **Ride pattern analysis** and demand forecasting
    - **Driver performance** metrics and rankings
    - **Revenue analytics** with financial insights
    - **Government compliance** reports
    - **Customer behavior** analysis

    ## 🚨 Error Handling
    All endpoints implement comprehensive error handling with:
    - **Standardized error codes** for client handling
    - **Detailed error messages** for debugging
    - **Retry mechanisms** for transient failures
    - **Circuit breaker patterns** for service resilience

    ## 🌐 Integration Capabilities
    - **Mobile money providers** (MTN, Airtel)
    - **Government systems** integration
    - **Third-party services** compatibility
    - **WebSocket** real-time communication

    ## 📚 API Versioning
    Current version: **v1** - Stable production API with backward compatibility

    ---

    **Contact Information:**
    - API Support: api-support@safeboda.rw
    - Documentation: docs.safeboda.rw
    - GitHub: github.com/safeboda-rwanda/platform
    ''',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': True,
        'defaultModelExpandDepth': 2,
        'defaultModelsExpandDepth': 2,
        'displayRequestDuration': True,
        'tryItOutEnabled': True,
        'filter': True,
        'requestSnippetsEnabled': True,
        'requestSnippets': {
            'generators': {
                'curl_bash': {
                    'title': 'cURL (bash)',
                    'syntax': 'bash'
                },
                'curl_powershell': {
                    'title': 'cURL (PowerShell)',
                    'syntax': 'powershell'
                },
                'curl_cmd': {
                    'title': 'cURL (CMD)',
                    'syntax': 'batch'
                }
            },
            'defaultExpanded': False,
            'languages': ['curl_bash', 'curl_powershell', 'curl_cmd']
        }
    },
    'REDOC_UI_SETTINGS': {
        'nativeScrollbars': True,
        'theme': {
            'colors': {
                'primary': {
                    'main': '#2E7D32'  # SafeBoda green
                }
            }
        }
    },
    'COMPONENT_SPLIT_REQUEST': True,
    'COMPONENT_NO_READ_ONLY_REQUIRED': True,
    'SCHEMA_PATH_PREFIX': '/api/',
    'SCHEMA_PATH_PREFIX_TRIM': True,
    'SERVERS': [
        {
            'url': 'http://localhost:8000',
            'description': 'Development server'
        },
        {
            'url': 'https://api.safeboda.rw',
            'description': 'Production server'
        },
        {
            'url': 'https://staging-api.safeboda.rw',
            'description': 'Staging server'
        }
    ],
    'TAGS': [
        {
            'name': 'Authentication',
            'description': 'User authentication and authorization endpoints'
        },
        {
            'name': 'Ride Booking',
            'description': 'Core ride booking and management functionality'
        },
        {
            'name': 'Real-time Tracking',
            'description': 'Live location tracking and driver positioning'
        },
        {
            'name': 'Payments',
            'description': 'Payment processing and mobile money integration'
        },
        {
            'name': 'Driver Management',
            'description': 'Driver onboarding, profile management, and performance'
        },
        {
            'name': 'Analytics',
            'description': 'Platform analytics and business intelligence'
        },
        {
            'name': 'Administrative Reports',
            'description': 'Government compliance and administrative reporting'
        },
        {
            'name': 'Notifications',
            'description': 'Push notifications and real-time messaging'
        },
        {
            'name': 'Government Integration',
            'description': 'Regulatory compliance and government reporting'
        },
        {
            'name': 'Monitoring',
            'description': 'System health and performance monitoring'
        }
    ],
    'EXTERNAL_DOCS': {
        'description': 'SafeBoda Rwanda Documentation',
        'url': 'https://docs.safeboda.rw/'
    },
    'CONTACT': {
        'name': 'SafeBoda Rwanda API Team',
        'url': 'https://safeboda.rw/contact',
        'email': 'api-support@safeboda.rw'
    },
    'LICENSE': {
        'name': 'Proprietary',
        'url': 'https://safeboda.rw/terms'
    },
    'SECURITY': [
        {
            'BearerAuth': []
        }
    ],
    'COMPONENTS': {
        'securitySchemes': {
            'BearerAuth': {
                'type': 'http',
                'scheme': 'bearer',
                'bearerFormat': 'JWT',
                'description': '''
                JWT authentication for SafeBoda Rwanda API.
                
                **How to obtain a token:**
                1. Register/login via `/api/auth/login/`
                2. Use the returned `access_token` in Authorization header
                3. Format: `Authorization: Bearer <your-jwt-token>`
                
                **Token expires in 24 hours** - refresh using `/api/auth/refresh/`
                '''
            }
        }
    }
}

# Enhanced schema customization for specific endpoints
class SafeBodaAutoSchema(AutoSchema):
    """Custom schema generation for SafeBoda Rwanda API"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.safeboda_examples = {
            'ride_create': {
                'pickup_location': {
                    'latitude': -1.9441,
                    'longitude': 30.0619,
                    'address': 'Kigali Convention Centre, Gasabo'
                },
                'destination_location': {
                    'latitude': -1.9481,
                    'longitude': 30.0927,
                    'address': 'Kimisagara Market, Nyarugenge'
                },
                'ride_type': 'standard',
                'payment_method': 'mtn_momo',
                'notes': 'Please wait at the main entrance'
            },
            'payment_mtn': {
                'phone_number': '+250788123456',
                'amount': 2500.00,
                'currency': 'RWF',
                'reference': 'RIDE_12345',
                'description': 'SafeBoda ride payment'
            },
            'driver_location': {
                'latitude': -1.9441,
                'longitude': 30.0619,
                'bearing': 45.0,
                'speed': 25.5,
                'accuracy': 5.0,
                'timestamp': '2025-10-17T15:30:00Z'
            }
        }
    
    def get_operation_id(self, path, method):
        """Generate operation IDs for SafeBoda endpoints"""
        operation_id = super().get_operation_id(path, method)
        
        # Add safeboda prefix for clarity
        if not operation_id.startswith('safeboda'):
            operation_id = f"safeboda_{operation_id}"
        
        return operation_id
    
    def get_examples(self, operation):
        """Add Rwanda-specific examples to endpoints"""
        examples = super().get_examples(operation)
        
        # Add context-specific examples
        path = getattr(self.path, 'pattern', '')
        
        if 'rides' in str(path):
            examples.update(self.safeboda_examples.get('ride_create', {}))
        elif 'payments' in str(path):
            examples.update(self.safeboda_examples.get('payment_mtn', {}))
        elif 'locations' in str(path):
            examples.update(self.safeboda_examples.get('driver_location', {}))
        
        return examples

# Common response schemas for reuse
COMMON_RESPONSES = {
    'unauthorized': {
        'description': 'Authentication required',
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'properties': {
                        'success': {'type': 'boolean', 'example': False},
                        'error': {'type': 'string', 'example': 'Authentication credentials were not provided'},
                        'error_code': {'type': 'string', 'example': 'AUTHENTICATION_REQUIRED'}
                    }
                }
            }
        }
    },
    'forbidden': {
        'description': 'Permission denied',
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'properties': {
                        'success': {'type': 'boolean', 'example': False},
                        'error': {'type': 'string', 'example': 'You do not have permission to perform this action'},
                        'error_code': {'type': 'string', 'example': 'PERMISSION_DENIED'}
                    }
                }
            }
        }
    },
    'not_found': {
        'description': 'Resource not found',
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'properties': {
                        'success': {'type': 'boolean', 'example': False},
                        'error': {'type': 'string', 'example': 'Resource not found'},
                        'error_code': {'type': 'string', 'example': 'NOT_FOUND'}
                    }
                }
            }
        }
    },
    'validation_error': {
        'description': 'Validation error',
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'properties': {
                        'success': {'type': 'boolean', 'example': False},
                        'error': {'type': 'string', 'example': 'Validation failed'},
                        'error_code': {'type': 'string', 'example': 'VALIDATION_ERROR'},
                        'errors': {
                            'type': 'object',
                            'example': {
                                'pickup_location': ['This field is required'],
                                'phone_number': ['Invalid phone number format']
                            }
                        }
                    }
                }
            }
        }
    },
    'server_error': {
        'description': 'Internal server error',
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'properties': {
                        'success': {'type': 'boolean', 'example': False},
                        'error': {'type': 'string', 'example': 'Internal server error'},
                        'error_code': {'type': 'string', 'example': 'INTERNAL_ERROR'}
                    }
                }
            }
        }
    }
}

# Rwanda-specific parameter patterns
RWANDA_PARAMETERS = {
    'phone_number': OpenApiParameter(
        name='phone_number',
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        description='Rwanda phone number in format +250XXXXXXXXX',
        pattern=r'^\+250[0-9]{9}$',
        example='+250788123456'
    ),
    'district': OpenApiParameter(
        name='district',
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        description='Rwanda district',
        enum=['Gasabo', 'Nyarugenge', 'Kicukiro'],
        example='Gasabo'
    ),
    'currency': OpenApiParameter(
        name='currency',
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        description='Currency code',
        enum=['RWF'],
        default='RWF'
    ),
    'language': OpenApiParameter(
        name='language',
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        description='Response language',
        enum=['en', 'rw', 'fr'],
        default='en'
    )
}

# Export commonly used decorators
def safeboda_api_view(summary: str, description: str = None, tags: list = None):
    """
    Decorator for SafeBoda API views with standard documentation
    """
    return extend_schema(
        summary=summary,
        description=description or summary,
        tags=tags or ['SafeBoda API'],
        responses={
            401: COMMON_RESPONSES['unauthorized'],
            403: COMMON_RESPONSES['forbidden'],
            404: COMMON_RESPONSES['not_found'],
            400: COMMON_RESPONSES['validation_error'],
            500: COMMON_RESPONSES['server_error']
        }
    )

def government_api_view(summary: str, description: str = None):
    """
    Decorator for government compliance API views
    """
    return extend_schema(
        summary=summary,
        description=description or summary,
        tags=['Government Integration', 'Administrative Reports'],
        responses={
            401: COMMON_RESPONSES['unauthorized'],
            403: COMMON_RESPONSES['forbidden'],
            500: COMMON_RESPONSES['server_error']
        }
    )

def realtime_api_view(summary: str, description: str = None):
    """
    Decorator for real-time API views with WebSocket info
    """
    return extend_schema(
        summary=summary,
        description=(description or summary) + "\n\n**Note:** This endpoint supports WebSocket connections for real-time updates.",
        tags=['Real-time Tracking', 'WebSocket'],
        responses={
            401: COMMON_RESPONSES['unauthorized'],
            404: COMMON_RESPONSES['not_found'],
            500: COMMON_RESPONSES['server_error']
        }
    )