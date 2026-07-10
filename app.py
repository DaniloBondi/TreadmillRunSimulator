from shiny import App, reactive, render, ui
import numpy as np
import matplotlib.pyplot as plt


app_ui = ui.page_sidebar(

    ui.sidebar(

        ui.h4("Runner Parameters"),

        ui.input_numeric(
            "mass",
            "Runner Mass (kg)",
            value=70,
            min=40,
            max=150
        ),

        ui.input_numeric(
            "velocity",
            "Velocity (m/s)",
            value=3.5,
            min=0.5,
            max=8.0,
            step=0.1
        ),

        ui.input_numeric(
            "grade",
            "Treadmill Grade (%)",
            value=5,
            min=-15,
            max=25,
            step=0.5
        ),

        ui.hr(),

        ui.h4("Metabolic Parameters"),

        ui.input_numeric(
            "vo2",
            "VO₂ (ml/kg/min)",
            value=40,
            min=5,
            max=90,
            step=0.5
        ),

        ui.input_numeric(
            "rer",
            "RER",
            value=0.90,
            min=0.7,
            max=1.0,
            step=0.01
        ),

        ui.hr(),

        ui.h4("Biomechanical Parameters"),

        ui.input_numeric(
            "stride_freq",
            "Stride Frequency (Hz)",
            value=1.5,
            min=0.8,
            max=2.5,
            step=0.1
        ),

        ui.input_numeric(
            "vertical_osc",
            "Vertical Oscillation (m)",
            value=0.08,
            min=0.03,
            max=0.15,
            step=0.005
        ),

        ui.input_numeric(
            "limb_mass_fraction",
            "Limb Mass Fraction",
            value=0.32,
            min=0.2,
            max=0.5,
            step=0.01
        ),

        ui.input_slider(
            "elastic_recovery",
            "Elastic Recovery Fraction",
            min=0.0,
            max=0.9,
            value=0.55,
            step=0.05
        ),

        ui.hr(),

        ui.h4("Energy Consumption Calculation"),

        ui.input_numeric(
            "distance",
            "Distance (km)",
            value=10,
            min=0.1,
            max=100,
            step=0.1
        ),

    ),

    ui.h2("Treadmill Running Efficiency Calculator"),

    ui.layout_columns(

        ui.card(
            ui.card_header("Mechanical Power"),
            ui.output_text_verbatim("mechanical_power_output")
        ),

        ui.card(
            ui.card_header("Metabolic Power"),
            ui.output_text_verbatim("metabolic_output")
        ),

        col_widths=[6, 6]
    ),

    ui.layout_columns(

        ui.card(
            ui.card_header("Efficiency"),
            ui.output_text_verbatim("efficiency_output")
        ),

        ui.card(
            ui.card_header("Energy Summary"),
            ui.output_text_verbatim("energy_output")
        ),

        col_widths=[6, 6]
    ),

    ui.card(
        ui.card_header("Total Energy Consumption"),
        ui.output_text_verbatim("total_energy_output")
    ),

    ui.card(
        ui.card_header("Mechanical vs Metabolic Power"),
        ui.output_plot("power_plot", height="500px")
    ),

    ui.card(
        ui.card_header("Mechanical Model"),
        ui.output_text_verbatim("details_output")
    )
)


def server(input, output, session):
  

    @reactive.calc
    def mechanical_power():

        mass = input.mass()
        velocity = input.velocity()
        grade = input.grade() / 100

        stride_freq = input.stride_freq()
        vertical_osc = input.vertical_osc()

        limb_mass_fraction = input.limb_mass_fraction()

        recovery_fraction = input.elastic_recovery()

        g = 9.81


        angle = np.arctan(grade)

        P_gravity = (
            mass *
            g *
            velocity *
            np.sin(angle)
        )


        A = vertical_osc / 2

        v_vertical_max = (
            2 *
            np.pi *
            stride_freq *
            A
        )

        E_vertical = (
            0.5 *
            mass *
            v_vertical_max**2
        )

        # Partial elastic recovery
        effective_recovery = (
            1 - (0.5 * recovery_fraction)
        )

        P_vertical = (
            E_vertical *
            stride_freq *
            effective_recovery
        )


        # Horizontal COM velocity fluctuation
        # Increases with slope

        delta_v = velocity * (
            0.22 + 0.8 * abs(grade)
        )

        E_forward = (
            0.5 *
            mass *
            delta_v**2
        )

        P_forward = (
            E_forward *
            stride_freq *
            effective_recovery
        )


        limb_mass = mass * limb_mass_fraction

        limb_velocity = velocity * 1.3

        P_limbs = (
            0.5 *
            limb_mass *
            limb_velocity**2 *
            stride_freq *
            0.35
        )


        P_total = (
            P_gravity +
            P_vertical +
            P_forward +
            P_limbs
        )

        return {
            "P_gravity": P_gravity,
            "P_vertical": P_vertical,
            "P_forward": P_forward,
            "P_limbs": P_limbs,
            "P_total": P_total
        }


    @reactive.calc
    def metabolic_power():

        mass = input.mass()
        vo2 = input.vo2()
        rer = input.rer()

        # Absolute VO2
        vo2_l_min = (
            vo2 *
            mass
        ) / 1000

        # Weir equation approximation
        kcal_per_l = (
            3.815 +
            1.232 * rer
        )

        kcal_min = (
            vo2_l_min *
            kcal_per_l
        )

        watts = kcal_min * 69.733

        return {
            "vo2_l_min": vo2_l_min,
            "kcal_per_l": kcal_per_l,
            "kcal_min": kcal_min,
            "watts": watts
        }

    @reactive.calc
    def efficiency():

        mech = mechanical_power()
        metab = metabolic_power()

        gross_eff = (
            mech["P_total"] /
            metab["watts"]
        ) * 100

        # Resting metabolic power
        resting_vo2 = 3.5

        resting_vo2_l = (
            resting_vo2 *
            input.mass()
        ) / 1000

        resting_power = (
            resting_vo2_l *
            metab["kcal_per_l"] *
            69.733
        )

        net_metabolic = (
            metab["watts"] -
            resting_power
        )

        net_eff = (
            mech["P_total"] /
            net_metabolic
        ) * 100

        # Physiological validation
        if gross_eff > 35:
            note = "Efficiency unusually high"

        elif gross_eff < 10:
            note = "Efficiency unusually low"

        else:
            note = "Efficiency within physiological range"

        return {
            "gross_eff": gross_eff,
            "net_eff": net_eff,
            "resting_power": resting_power,
            "note": note
        }

    @reactive.calc
    def total_energy_consumption():

        metab = metabolic_power()
        distance = input.distance()
        velocity = input.velocity()
        mass = input.mass()
        vo2 = input.vo2()

        # Calculate time to cover distance (in seconds)
        distance_m = distance * 1000
        time_seconds = distance_m / velocity

        # Total VO2 consumption in ml
        # vo2 is in ml/kg/min, mass in kg
        vo2_per_min = (vo2 * mass)
        time_minutes = time_seconds / 60
        total_vo2_ml = vo2_per_min * time_minutes

        # Total kcal consumption
        total_kcal = metab["kcal_min"] * time_minutes

        # Total Joules
        # 1 kcal = 4184 Joules
        total_joules = total_kcal * 4184

        # Total energy in watts·hours
        total_wh = (metab["watts"] * time_seconds) / 3600

        return {
            "distance": distance,
            "time_minutes": time_minutes,
            "time_hours": time_minutes / 60,
            "total_vo2_ml": total_vo2_ml,
            "total_kcal": total_kcal,
            "total_joules": total_joules,
            "total_wh": total_wh
        }


    @output
    @render.text
    def mechanical_power_output():

        mech = mechanical_power()

        return (
            f"Gravity Power: "
            f"{mech['P_gravity']:.1f} W\n\n"

            f"Vertical COM Power: "
            f"{mech['P_vertical']:.1f} W\n\n"

            f"Forward COM Power: "
            f"{mech['P_forward']:.1f} W\n\n"

            f"Limb/Internal Power: "
            f"{mech['P_limbs']:.1f} W\n\n"

            f"----------------------------------\n"

            f"TOTAL MECHANICAL POWER:\n"
            f"{mech['P_total']:.1f} W"
        )

    @output
    @render.text
    def metabolic_output():

        metab = metabolic_power()

        return (
            f"VO₂ Absolute:\n"
            f"{metab['vo2_l_min']:.2f} L/min\n\n"

            f"Energy Equivalent:\n"
            f"{metab['kcal_per_l']:.2f} kcal/L O₂\n\n"

            f"Metabolic Power:\n"
            f"{metab['watts']:.1f} W\n\n"

            f"Energy Expenditure:\n"
            f"{metab['kcal_min']:.2f} kcal/min"
        )

    @output
    @render.text
    def efficiency_output():

        eff = efficiency()

        return (
            f"Gross Efficiency:\n"
            f"{eff['gross_eff']:.2f}%\n\n"

            f"Net Efficiency:\n"
            f"{eff['net_eff']:.2f}%\n\n"

            f"Resting Metabolic Power:\n"
            f"{eff['resting_power']:.1f} W\n\n"

            f"{eff['note']}"
        )

    @output
    @render.text
    def energy_output():

        mech = mechanical_power()
        metab = metabolic_power()

        heat = (
            metab["watts"] -
            mech["P_total"]
        )

        return (
            f"Metabolic Input:\n"
            f"{metab['watts']:.1f} W\n\n"

            f"Mechanical Output:\n"
            f"{mech['P_total']:.1f} W\n\n"

            f"Dissipated Energy (Heat):\n"
            f"{heat:.1f} W\n\n"

            f"Hourly Energy Cost:\n"
            f"{metab['kcal_min'] * 60:.1f} kcal/h"
        )

    @output
    @render.text
    def total_energy_output():

        total = total_energy_consumption()

        return (
            f"Distance: {total['distance']:.1f} km\n"
            f"Estimated Time: {total['time_hours']:.2f} hours "
            f"({int(total['time_minutes'])} minutes)\n\n"

            f"----------------------------------\n"

            f"TOTAL VO₂ CONSUMPTION:\n"
            f"{total['total_vo2_ml']:,.0f} ml\n\n"

            f"TOTAL ENERGY EXPENDITURE:\n"
            f"{total['total_kcal']:,.1f} kcal\n\n"

            f"TOTAL ENERGY (JOULES):\n"
            f"{total['total_joules']:,.0f} J\n\n"

            f"TOTAL ENERGY (WATT·HOURS):\n"
            f"{total['total_wh']:,.1f} Wh"
        )


    @output
    @render.plot
    def power_plot():

        mech = mechanical_power()
        metab = metabolic_power()

        categories = ["Mechanical components", "Metabolic power"]

        gravity = mech["P_gravity"]
        vertical = mech["P_vertical"]
        forward = mech["P_forward"]
        limbs = mech["P_limbs"]

        metabolic = metab["watts"]

        # stacked components
        mechanical_components = [
            gravity,
            vertical,
            forward,
            limbs
        ]

        labels = ["Gravity", "Vertical COM", "Forward COM", "Limbs"]
        colors = ["steelblue", "orange", "green", "purple"]

        fig, ax = plt.subplots(figsize=(10, 5))

        bottom = 0
        bars = []

        for val, col, lab in zip(mechanical_components, colors, labels):

            ax.bar(
                categories[0],
                val,
                bottom=bottom,
                color=col,
                label=lab
            )

            bottom += val

        ax.bar(
            categories[1],
            metabolic,
            color="red",
            label="Metabolic Power"
        )

        ax.set_ylabel("Power (W)")
        ax.set_title("Mechanical vs Metabolic Power (Stacked Breakdown)")

        ax.legend(loc="upper right")

        # value annotations
        ax.text(
            0,
            bottom,
            f"{bottom:.0f} W",
            ha="center",
            va="bottom",
            fontweight="bold"
        )

        ax.text(
            1,
            metabolic,
            f"{metabolic:.0f} W",
            ha="center",
            va="bottom",
            fontweight="bold"
        )

        plt.tight_layout()

        return fig

    @output
    @render.text
    def details_output():

        return (
            "MECHANICAL MODEL\n"
            "============================\n\n"

            "1. Gravity Power\n"
            "Mechanical work required to\n"
            "move the body uphill.\n\n"

            "P = m · g · v · sin(theta)\n\n"

            "2. Vertical COM Power\n"
            "Energy associated with vertical\n"
            "oscillation of the center of mass.\n\n"

            "3. Forward COM Power\n"
            "Mechanical work associated with\n"
            "braking and propulsion.\n\n"

            "4. Limb/Internal Power\n"
            "Internal work required to swing\n"
            "and accelerate the limbs.\n\n"

            "5. Elastic Return\n"
            "Part of the mechanical energy\n"
            "is temporarily stored in tendons,\n"
            "muscles and footwear.\n\n"

            "Elastic recoil reduces active\n"
            "muscular work and improves\n"
            "running economy.\n\n"

            "6. Metabolic Power\n"
            "Calculated from VO₂ and RER.\n\n"

            "7. Efficiency\n"
            "Mechanical Power / Metabolic Power\n\n"

            "Typical gross efficiency:\n"
            "20–30%\n\n"

            "NOTE:\n"
            "This model is a simplified estimate\n"
            "inspired by treadmill biomechanics\n"
            "and locomotion energetics literature."
        )


app = App(app_ui, server)
