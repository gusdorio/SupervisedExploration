"""
Main ML Model Processing Pipeline
Orchestrates data cleaning and model training/predictions
"""

import os
import sys
import pandas as pd
import json
from datetime import datetime
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml_model.classes.datacleaner import ICBDataCleaner
from ml_model.classes.algorithms import AnalisadorCestaBasicaPro


class MLPipeline:
    """
    Main pipeline for ML model processing.
    Coordinates data cleaning and model predictions.
    """

    def __init__(self, raw_data_path: str = 'data/ICB_2s-2025.xlsx'):
        """Initialize the pipeline with data path."""
        self.raw_data_path = raw_data_path
        self.cleaned_data_path = 'data/dados_limpos_ICB.xlsx'
        self.results_dir = 'data/results'
        os.makedirs(self.results_dir, exist_ok=True)

    def run_data_cleaning(self) -> pd.DataFrame:
        """Execute the data cleaning pipeline."""
        print("\n" + "=" * 60)
        print("PHASE 1: DATA CLEANING")
        print("=" * 60)

        cleaner = ICBDataCleaner(self.raw_data_path)
        df_clean, mappings = cleaner.process()

        print(f"\nData cleaning completed!")
        print(f"  - Clean data saved to: {self.cleaned_data_path}")
        print(f"  - Mappings saved to: data/mapa_*.json")

        return df_clean

    def run_model_predictions(self) -> Dict[str, Any]:
        """Run model predictions for all categories."""
        print("\n" + "=" * 60)
        print("PHASE 2: MODEL TRAINING AND PREDICTIONS")
        print("=" * 60)

        # Initialize the analyzer
        analisador = AnalisadorCestaBasicaPro(self.cleaned_data_path)

        # List of categories to analyze (from Q1)
        categorias = [
            "Classe_Carnes Vermelhas",
            "Classe_Grãos & Massas",
            "Classe_Laticínios",
            "Classe_Padaria & Cozinha",
            "Classe_Vegetais"
        ]

        results = {}

        for categoria in categorias:
            print(f"\nProcessing category: {categoria}")
            print("-" * 40)

            try:
                # Run prediction analysis
                df_plot, mse, mae, mape, df_futuro, erro = analisador.analisar_previsao_categoria(
                    nome_categoria=categoria,
                    test_size_semanas=12,
                    freq='W-MON',
                    n_lags=4
                )

                if erro:
                    print(f"  Error: {erro}")
                    results[categoria] = {'error': erro}
                    continue

                # Calculate MAPE percentage
                mape_percent = mape * 100

                # Store results
                results[categoria] = {
                    'mse': float(mse),
                    'mae': float(mae),
                    'mape': float(mape),
                    'mape_percent': float(mape_percent),
                    'objetivo_atingido': mape_percent < 10,
                    'predictions': df_futuro.to_dict() if df_futuro is not None else None
                }

                print(f"  MSE: {mse:.4f}")
                print(f"  MAE: {mae:.4f}")
                print(f"  MAPE: {mape_percent:.2f}%")
                print(f"  Objective (<10% MAPE): {'✓ ACHIEVED' if mape_percent < 10 else '✗ NOT ACHIEVED'}")

                # Save predictions to CSV
                if df_futuro is not None:
                    output_file = os.path.join(self.results_dir, f'predictions_{categoria.replace(" ", "_")}.csv')
                    df_futuro.to_csv(output_file)
                    print(f"  Predictions saved to: {output_file}")

            except Exception as e:
                print(f"  Error processing {categoria}: {str(e)}")
                results[categoria] = {'error': str(e)}

        return results

    def save_results(self, results: Dict[str, Any]) -> None:
        """Save processing results to JSON."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = os.path.join(self.results_dir, f'model_results_{timestamp}.json')

        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"\nResults saved to: {results_file}")

    def generate_summary_report(self, results: Dict[str, Any]) -> None:
        """Generate a summary report of model performance."""
        print("\n" + "=" * 60)
        print("MODEL PERFORMANCE SUMMARY")
        print("=" * 60)

        successful = 0
        failed = 0
        objectives_met = 0

        for category, result in results.items():
            if 'error' in result:
                failed += 1
                print(f"\n{category}: FAILED - {result['error']}")
            else:
                successful += 1
                mape_percent = result['mape_percent']
                met = result['objetivo_atingido']

                if met:
                    objectives_met += 1

                status = "✓" if met else "✗"
                print(f"\n{category}:")
                print(f"  MAPE: {mape_percent:.2f}% {status}")
                print(f"  MSE: {result['mse']:.4f}")
                print(f"  MAE: {result['mae']:.4f}")

        print("\n" + "-" * 60)
        print(f"TOTAL CATEGORIES: {len(results)}")
        print(f"  Successful: {successful}")
        print(f"  Failed: {failed}")
        print(f"  Objectives Met (<10% MAPE): {objectives_met}/{successful}")
        print("=" * 60)

    def run(self) -> None:
        """Execute the complete ML pipeline."""
        print("\n" + "#" * 60)
        print("STARTING ML MODEL PIPELINE")
        print("#" * 60)

        start_time = datetime.now()

        try:
            # Phase 1: Data Cleaning
            df_clean = self.run_data_cleaning()

            # Phase 2: Model Training and Predictions
            results = self.run_model_predictions()

            # Save results
            self.save_results(results)

            # Generate summary report
            self.generate_summary_report(results)

        except Exception as e:
            print(f"\nPIPELINE ERROR: {str(e)}")
            raise

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        print(f"\nPipeline completed in {duration:.2f} seconds")
        print("#" * 60)


def main():
    """Main entry point."""
    # Check if raw data exists
    raw_data_path = 'data/ICB_2s-2025.xlsx'

    if not os.path.exists(raw_data_path):
        print(f"ERROR: Raw data file not found at {raw_data_path}")
        print("Please ensure the data file is in the correct location.")
        sys.exit(1)

    # Run the pipeline
    pipeline = MLPipeline(raw_data_path)
    pipeline.run()


if __name__ == "__main__":
    main()