// MongoDB Initialization Script for ICB ML Database

// Switch to icb_ml database
db = db.getSiblingDB('icb_ml');

// Create collections with validation schemas
db.createCollection('ml_training_results', {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["batch_id", "category", "metrics"],
      properties: {
        batch_id: { bsonType: "string" },
        category: { bsonType: "string" },
        metrics: {
          bsonType: "object",
          required: ["mse", "mae", "mape"],
          properties: {
            mse: { bsonType: "double" },
            mae: { bsonType: "double" },
            mape: { bsonType: "double" }
          }
        }
      }
    }
  }
});

db.createCollection('category_predictions', {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["batch_id", "category", "predictions"],
      properties: {
        batch_id: { bsonType: "string" },
        category: { bsonType: "string" },
        predictions: {
          bsonType: "array",
          items: {
            bsonType: "object",
            required: ["week", "predicted_value"],
            properties: {
              week: { bsonType: "date" },
              predicted_value: { bsonType: "double" }
            }
          }
        }
      }
    }
  }
});

db.createCollection('price_leadership_analyses');
db.createCollection('pipeline_runs');

// Create indexes for better query performance
db.ml_training_results.createIndex({ "batch_id": 1, "category": 1 });
db.ml_training_results.createIndex({ "timestamp": -1 });

db.category_predictions.createIndex({ "batch_id": 1, "category": 1 });
db.category_predictions.createIndex({ "created_at": -1 });

db.price_leadership_analyses.createIndex({ "batch_id": 1 });
db.price_leadership_analyses.createIndex({ "product_id": 1 });

db.pipeline_runs.createIndex({ "batch_id": 1 }, { unique: true });
db.pipeline_runs.createIndex({ "status": 1 });
db.pipeline_runs.createIndex({ "started_at": -1 });

print('MongoDB initialization completed successfully');