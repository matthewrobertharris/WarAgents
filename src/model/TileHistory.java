package model;

public class TileHistory {

	private int dirt;
	private int food;
	private Agent agent;
	private Plant plant;
	private int time;

	public TileHistory(Tile tile, int time) {
		this(tile.getDirt(), tile.getFood(), tile.getAgent(), tile.getPlant(), time);
	}

	public TileHistory(int dirt, int food, Agent agent, Plant plant, int time) {
		setDirt(dirt);
		setFood(food);
		setAgent(agent);
		setPlant(plant);
		setTime(time);
	}

	public int getTime() {
		return time;
	}

	public void setTime(int time) {
		this.time = time;
	}

	public int getDirt() {
		return dirt;
	}

	public void setDirt(int dirt) {
		this.dirt = dirt;
	}

	public int getFood() {
		return food;
	}

	public void setFood(int food) {
		this.food = food;
	}

	public Agent getAgent() {
		return agent;
	}

	public void setAgent(Agent agent) {
		this.agent = agent;
	}

	public Plant getPlant() {
		return plant;
	}

	public void setPlant(Plant plant) {
		this.plant = plant;
	}

}
