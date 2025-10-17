#!/usr/bin/env python
"""
OpenAPI Schema Generation Script for SafeBoda Rwanda Platform
Generates comprehensive API documentation with Rwanda-specific examples
"""
import os
import sys
import json
import yaml
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'safeboda_rwanda.settings.development')

import django
django.setup()

from drf_spectacular.openapi import AutoSchema
from drf_spectacular.generators import SchemaGenerator
from django.urls import reverse
from django.test import RequestFactory
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)


class SafeBodaSchemaGenerator:
    """Generate comprehensive OpenAPI schema for SafeBoda Rwanda"""
    
    def __init__(self):
        self.factory = RequestFactory()
        self.generator = SchemaGenerator(
            title='SafeBoda Rwanda API',
            description='Complete ride-booking platform API for Rwanda',
            version='1.0.0',
            patterns=None
        )
        self.docs_dir = project_root / 'docs'
        self.docs_dir.mkdir(exist_ok=True)
    
    def generate_schema(self) -> dict:
        """Generate the complete OpenAPI schema"""
        print("🚀 Generating SafeBoda Rwanda API schema...")
        
        # Create a fake request for schema generation
        request = self.factory.get('/')
        
        # Generate the schema
        schema = self.generator.get_schema(request=request, public=True)
        
        # Enhance with Rwanda-specific information
        schema = self._enhance_schema(schema)
        
        print(f"✅ Generated schema with {len(schema.get('paths', {}))} endpoints")
        return schema
    
    def _enhance_schema(self, schema: dict) -> dict:
        """Enhance schema with Rwanda-specific information"""
        
        # Add Rwanda-specific server information
        schema['servers'] = [
            {
                'url': 'http://localhost:8000',
                'description': 'Development server (Kigali)'
            },
            {
                'url': 'https://api.safeboda.rw',
                'description': 'Production server (Rwanda)'
            },
            {
                'url': 'https://staging-api.safeboda.rw',
                'description': 'Staging server (Rwanda)'
            }
        ]
        
        # Add contact information
        schema['info']['contact'] = {
            'name': 'SafeBoda Rwanda API Team',
            'url': 'https://safeboda.rw/contact',
            'email': 'api-support@safeboda.rw'
        }
        
        # Add license information
        schema['info']['license'] = {
            'name': 'Proprietary - SafeBoda Rwanda',
            'url': 'https://safeboda.rw/terms'
        }
        
        # Add external documentation
        schema['externalDocs'] = {
            'description': 'SafeBoda Rwanda Platform Documentation',
            'url': 'https://docs.safeboda.rw'
        }
        
        # Enhance path descriptions with Rwanda context
        if 'paths' in schema:
            schema['paths'] = self._enhance_paths(schema['paths'])
        
        # Add Rwanda-specific components
        if 'components' not in schema:
            schema['components'] = {}
        
        schema['components']['schemas'].update(self._get_rwanda_schemas())
        
        # Add security schemes
        schema['components']['securitySchemes'] = {
            'BearerAuth': {
                'type': 'http',
                'scheme': 'bearer',
                'bearerFormat': 'JWT',
                'description': 'JWT authentication for SafeBoda Rwanda API'
            }
        }
        
        # Add global security requirement
        schema['security'] = [{'BearerAuth': []}]
        
        return schema
    
    def _enhance_paths(self, paths: dict) -> dict:
        """Enhance API paths with Rwanda-specific context"""
        
        enhanced_paths = {}
        
        for path, methods in paths.items():
            enhanced_methods = {}
            
            for method, operation in methods.items():
                if isinstance(operation, dict):
                    # Add Rwanda-specific examples
                    if 'examples' not in operation:
                        operation['examples'] = {}
                    
                    # Add context-specific examples
                    if 'rides' in path:
                        operation = self._add_ride_examples(operation)
                    elif 'payments' in path:
                        operation = self._add_payment_examples(operation)
                    elif 'locations' in path:
                        operation = self._add_location_examples(operation)
                    elif 'analytics' in path:
                        operation = self._add_analytics_examples(operation)
                    
                    # Add Rwanda-specific tags
                    if 'tags' in operation:
                        if any('government' in tag.lower() for tag in operation['tags']):
                            operation['tags'].append('Rwanda Compliance')
                        if any('payment' in tag.lower() for tag in operation['tags']):
                            operation['tags'].append('Mobile Money Rwanda')
                
                enhanced_methods[method] = operation
            
            enhanced_paths[path] = enhanced_methods
        
        return enhanced_paths
    
    def _add_ride_examples(self, operation: dict) -> dict:
        """Add Rwanda-specific ride booking examples"""
        
        if 'requestBody' in operation:
            content = operation['requestBody'].get('content', {})
            if 'application/json' in content:
                content['application/json']['examples'] = {
                    'kigali_city_ride': {
                        'summary': 'Kigali city center ride',
                        'description': 'Typical ride within Kigali city center',
                        'value': {
                            'pickup_location': {
                                'latitude': -1.9441,
                                'longitude': 30.0619,
                                'address': 'Kigali Convention Centre, Gasabo District'
                            },
                            'destination_location': {
                                'latitude': -1.9486,
                                'longitude': 30.0588,
                                'address': 'Union Trade Centre, Gasabo District'
                            },
                            'ride_type': 'standard',
                            'payment_method': 'mtn_momo',
                            'notes': 'Please wait at the main entrance'
                        }
                    },
                    'airport_ride': {
                        'summary': 'Airport transfer',
                        'description': 'Ride from city to Kigali International Airport',
                        'value': {
                            'pickup_location': {
                                'latitude': -1.9441,
                                'longitude': 30.0619,
                                'address': 'Kigali City Centre'
                            },
                            'destination_location': {
                                'latitude': -2.0117,
                                'longitude': 30.1395,
                                'address': 'Kigali International Airport'
                            },
                            'ride_type': 'premium',
                            'payment_method': 'airtel_money',
                            'notes': 'Flight departure at 14:30, terminal 1'
                        }
                    }
                }
        
        return operation
    
    def _add_payment_examples(self, operation: dict) -> dict:
        """Add Rwanda mobile money payment examples"""
        
        if 'requestBody' in operation:
            content = operation['requestBody'].get('content', {})
            if 'application/json' in content:
                content['application/json']['examples'] = {
                    'mtn_momo_payment': {
                        'summary': 'MTN Mobile Money payment',
                        'description': 'Payment using MTN Mobile Money Rwanda',
                        'value': {
                            'phone_number': '+250788123456',
                            'amount': 2500.00,
                            'currency': 'RWF',
                            'provider': 'mtn_momo',
                            'reference': 'RIDE_12345'
                        }
                    },
                    'airtel_money_payment': {
                        'summary': 'Airtel Money payment',
                        'description': 'Payment using Airtel Money Rwanda',
                        'value': {
                            'phone_number': '+250732654321',
                            'amount': 3200.00,
                            'currency': 'RWF',
                            'provider': 'airtel_money',
                            'reference': 'RIDE_67890'
                        }
                    }
                }
        
        return operation
    
    def _add_location_examples(self, operation: dict) -> dict:
        """Add Rwanda location tracking examples"""
        
        if 'requestBody' in operation:
            content = operation['requestBody'].get('content', {})
            if 'application/json' in content:
                content['application/json']['examples'] = {
                    'kigali_location': {
                        'summary': 'Kigali city location',
                        'description': 'Driver location in Kigali city',
                        'value': {
                            'latitude': -1.9441,
                            'longitude': 30.0619,
                            'bearing': 45.0,
                            'speed': 25.5,
                            'accuracy': 5.0,
                            'district': 'Gasabo',
                            'timestamp': '2025-10-17T15:30:00Z'
                        }
                    },
                    'suburb_location': {
                        'summary': 'Suburban location',
                        'description': 'Driver location in suburban area',
                        'value': {
                            'latitude': -1.9800,
                            'longitude': 30.1200,
                            'bearing': 180.0,
                            'speed': 40.0,
                            'accuracy': 10.0,
                            'district': 'Kicukiro',
                            'timestamp': '2025-10-17T15:30:00Z'
                        }
                    }
                }
        
        return operation
    
    def _add_analytics_examples(self, operation: dict) -> dict:
        """Add Rwanda analytics examples"""
        
        # Analytics examples would include Rwanda-specific data patterns
        return operation
    
    def _get_rwanda_schemas(self) -> dict:
        """Get Rwanda-specific schema components"""
        
        return {
            'RwandaLocation': {
                'type': 'object',
                'properties': {
                    'latitude': {
                        'type': 'number',
                        'format': 'double',
                        'minimum': -2.5,
                        'maximum': -1.0,
                        'description': 'Latitude coordinate within Rwanda'
                    },
                    'longitude': {
                        'type': 'number',
                        'format': 'double',
                        'minimum': 29.0,
                        'maximum': 31.0,
                        'description': 'Longitude coordinate within Rwanda'
                    },
                    'district': {
                        'type': 'string',
                        'enum': ['Gasabo', 'Nyarugenge', 'Kicukiro'],
                        'description': 'Rwanda district'
                    },
                    'address': {
                        'type': 'string',
                        'description': 'Human-readable address in Rwanda'
                    }
                },
                'required': ['latitude', 'longitude']
            },
            'RwandaPhoneNumber': {
                'type': 'string',
                'pattern': r'^\\+250[0-9]{9}$',
                'description': 'Rwanda phone number in international format',
                'example': '+250788123456'
            },
            'MobileMoneyProvider': {
                'type': 'string',
                'enum': ['mtn_momo', 'airtel_money', 'cash'],
                'description': 'Available payment methods in Rwanda'
            },
            'RwandaCurrency': {
                'type': 'string',
                'enum': ['RWF'],
                'description': 'Rwanda Franc currency code'
            },
            'GovernmentCompliance': {
                'type': 'object',
                'properties': {
                    'bnr_reporting': {
                        'type': 'boolean',
                        'description': 'Bank of Rwanda reporting compliance'
                    },
                    'rra_tax_compliance': {
                        'type': 'boolean',
                        'description': 'Rwanda Revenue Authority tax compliance'
                    },
                    'rtda_license_valid': {
                        'type': 'boolean',
                        'description': 'Rwanda Transport Development Agency license validity'
                    }
                }
            }
        }
    
    def save_schema(self, schema: dict, format_type: str = 'both'):
        """Save schema to files"""
        
        if format_type in ['json', 'both']:
            json_file = self.docs_dir / 'openapi.json'
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(schema, f, indent=2, ensure_ascii=False)
            print(f"📄 Saved JSON schema to: {json_file}")
        
        if format_type in ['yaml', 'both']:
            yaml_file = self.docs_dir / 'openapi.yaml'
            with open(yaml_file, 'w', encoding='utf-8') as f:
                yaml.dump(schema, f, default_flow_style=False, allow_unicode=True)
            print(f"📄 Saved YAML schema to: {yaml_file}")
    
    def generate_postman_collection(self, schema: dict):
        """Generate Postman collection from OpenAPI schema"""
        
        collection = {
            'info': {
                'name': 'SafeBoda Rwanda API',
                'description': schema['info']['description'],
                'version': schema['info']['version'],
                'schema': 'https://schema.getpostman.com/json/collection/v2.1.0/collection.json'
            },
            'auth': {
                'type': 'bearer',
                'bearer': [
                    {
                        'key': 'token',
                        'value': '{{jwt_token}}',
                        'type': 'string'
                    }
                ]
            },
            'variable': [
                {
                    'key': 'base_url',
                    'value': 'http://localhost:8000',
                    'type': 'string'
                },
                {
                    'key': 'jwt_token',
                    'value': '',
                    'type': 'string'
                }
            ],
            'item': []
        }
        
        # Convert OpenAPI paths to Postman requests
        for path, methods in schema.get('paths', {}).items():
            folder = {
                'name': path.strip('/').replace('/', ' - '),
                'item': []
            }
            
            for method, operation in methods.items():
                if isinstance(operation, dict):
                    request = {
                        'name': operation.get('summary', f"{method.upper()} {path}"),
                        'request': {
                            'method': method.upper(),
                            'header': [
                                {
                                    'key': 'Content-Type',
                                    'value': 'application/json'
                                }
                            ],
                            'url': {
                                'raw': '{{base_url}}' + path,
                                'host': ['{{base_url}}'],
                                'path': path.strip('/').split('/')
                            }
                        }
                    }
                    
                    # Add request body if present
                    if 'requestBody' in operation:
                        content = operation['requestBody'].get('content', {})
                        if 'application/json' in content:
                            examples = content['application/json'].get('examples', {})
                            if examples:
                                first_example = list(examples.values())[0]
                                request['request']['body'] = {
                                    'mode': 'raw',
                                    'raw': json.dumps(first_example.get('value', {}), indent=2)
                                }
                    
                    folder['item'].append(request)
            
            if folder['item']:
                collection['item'].append(folder)
        
        # Save Postman collection
        postman_file = self.docs_dir / 'postman_collection.json'
        with open(postman_file, 'w', encoding='utf-8') as f:
            json.dump(collection, f, indent=2, ensure_ascii=False)
        
        print(f"📮 Saved Postman collection to: {postman_file}")
    
    def generate_readme(self, schema: dict):
        """Generate comprehensive API documentation README"""
        
        readme_content = f"""# SafeBoda Rwanda API Documentation

{schema['info']['description']}

## 🚀 Quick Start

### Authentication
```bash
# Login to get JWT token
curl -X POST http://localhost:8000/api/auth/login/ \\
  -H "Content-Type: application/json" \\
  -d '{{"phone_number": "+250788123456", "password": "your_password"}}'

# Use token in subsequent requests
curl -X GET http://localhost:8000/api/rides/ \\
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Book a Ride
```bash
curl -X POST http://localhost:8000/api/rides/ \\
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "pickup_location": {{
      "latitude": -1.9441,
      "longitude": 30.0619,
      "address": "Kigali Convention Centre"
    }},
    "destination_location": {{
      "latitude": -1.9486,
      "longitude": 30.0588,
      "address": "Union Trade Centre"
    }},
    "ride_type": "standard",
    "payment_method": "mtn_momo"
  }}'
```

### Process Payment
```bash
curl -X POST http://localhost:8000/api/payments/process/ \\
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "phone_number": "+250788123456",
    "amount": 2500.00,
    "provider": "mtn_momo",
    "reference": "RIDE_12345"
  }}'
```

## 📚 API Documentation

- **OpenAPI Specification**: [openapi.json](./openapi.json) | [openapi.yaml](./openapi.yaml)
- **Postman Collection**: [postman_collection.json](./postman_collection.json)
- **Interactive Docs**: http://localhost:8000/api/docs/
- **ReDoc**: http://localhost:8000/api/redoc/

## 🏛️ Government Compliance

SafeBoda Rwanda complies with:
- **Bank of Rwanda (BNR)** financial reporting requirements
- **Rwanda Revenue Authority (RRA)** tax compliance
- **Rwanda Transport Development Agency (RTDA)** licensing

## 🔐 Security

- JWT-based authentication with 24-hour expiry
- Role-based access control (Customer, Driver, Admin, Government)
- HTTPS enforced in production
- API rate limiting implemented

## 🌍 Rwanda-Specific Features

- **Districts**: Gasabo, Nyarugenge, Kicukiro
- **Mobile Money**: MTN Mobile Money, Airtel Money
- **Currency**: Rwanda Franc (RWF)
- **Languages**: English, Kinyarwanda, French

## 📊 Analytics Endpoints

- Ride pattern analysis
- Driver performance metrics
- Revenue analytics
- Government compliance reports

## 🔄 Real-time Features

- WebSocket connections for live tracking
- Push notifications for ride updates
- Live driver positioning
- Real-time payment processing

## 📱 Integration

### Mobile Money Integration
- MTN Mobile Money API integration
- Airtel Money API integration
- Real-time payment status updates
- Automatic reconciliation

### Government Systems
- Automated compliance reporting
- Tax calculation and submission
- Regulatory audit trails
- License validation

## 🛠️ Development

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Start development server
python manage.py runserver
```

### Generate Documentation
```bash
# Generate OpenAPI schema
python docs/generate_openapi.py

# Update API documentation
python manage.py spectacular --color --file docs/openapi.yaml
```

## 📞 Support

- **API Support**: api-support@safeboda.rw
- **Documentation**: https://docs.safeboda.rw
- **Issues**: https://github.com/safeboda-rwanda/platform/issues

## 📄 License

Proprietary - SafeBoda Rwanda Limited

---

Generated on: {schema.get('info', {}).get('version', 'unknown')}
"""
        
        readme_file = self.docs_dir / 'API_README.md'
        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        print(f"📖 Saved API README to: {readme_file}")


def main():
    """Main function to generate all documentation"""
    
    print("🚀 SafeBoda Rwanda API Documentation Generator")
    print("=" * 50)
    
    try:
        generator = SafeBodaSchemaGenerator()
        
        # Generate OpenAPI schema
        schema = generator.generate_schema()
        
        # Save in different formats
        generator.save_schema(schema, 'both')
        
        # Generate Postman collection
        generator.generate_postman_collection(schema)
        
        # Generate README
        generator.generate_readme(schema)
        
        print("\n✅ Documentation generation completed successfully!")
        print("\nGenerated files:")
        print("📄 docs/openapi.json - OpenAPI 3.0 specification (JSON)")
        print("📄 docs/openapi.yaml - OpenAPI 3.0 specification (YAML)")
        print("📮 docs/postman_collection.json - Postman collection")
        print("📖 docs/API_README.md - Comprehensive API documentation")
        
        print("\n🌐 View documentation:")
        print("• Interactive docs: http://localhost:8000/api/docs/")
        print("• ReDoc: http://localhost:8000/api/redoc/")
        
    except Exception as e:
        print(f"❌ Error generating documentation: {str(e)}")
        logger.error(f"Documentation generation failed: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()