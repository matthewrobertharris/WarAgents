package model;

import java.util.ArrayList;
import java.util.List;

public class Tile {

	private int dirt;
	private int food;
	private Agent agent;
	private Plant plant;
	private List<TileHistory> history;

	public static final int MAX_DIRT = 15;
	public static final int MIN_DIRT = 0;
	public static final int MAX_FOOD = 100;
	public static final int MIN_FOOD = 0;

	public Tile(int dirt, int food, Agent occupied, Plant plant) {
		setDirt(dirt);
		setFood(food);
		setAgent(occupied);
		setPlant(plant);
		setHistory(new ArrayList<TileHistory>());
		addHistory(0);
	}

	public void addHistory(int time) {
		getHistory().add(new TileHistory(this, time));
	}

	public List<TileHistory> getHistory() {
		return history;
	}

	public void setHistory(List<TileHistory> history) {
		this.history = history;
	}

	public Plant getPlant() {
		return plant;
	}

	public void setPlant(Plant plant) {
		this.plant = plant;
	}

	public int getDirt() {
		return dirt;
	}

	public void setDirt(int dirt) {
		this.dirt = dirt;
		if (getDirt() < MIN_DIRT) {
			this.dirt = MIN_DIRT;
		}
		if (getDirt() > MAX_DIRT) {
			this.dirt = MAX_DIRT;
		}
	}

	public int getFood() {
		return food;
	}

	public void setFood(int food) {
		this.food = food;
		if (getFood() < 0) {
			this.food = 0;
		}
		if (getFood() > MAX_FOOD) {
			this.food = MAX_FOOD;
		}
	}

	public void addFood(int food) {
		setFood(getFood() + food);
	}

	public Agent getAgent() {
		return agent;
	}

	public void setAgent(Agent agent) {
		this.agent = agent;
	}

	public boolean isOccupied() {
		return getAgent() != null;
	}

	public String toString() {
		String output = "Dirt=" + getDirt();
		output += " Food=" + getFood();
		if (getPlant() != null) {
			output += " Plant=" + getPlant().getID();
		}
		// else {
		// output += " Plant=null";
		// }
		if (isOccupied()) {
			output += " Agent=" + getAgent().getID();
		}
		// else {
		// output += " Occupied=null";
		// }
		return output;
	}
}
