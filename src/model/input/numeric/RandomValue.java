package model.input.numeric;

import java.util.Random;

import main.Game;
import model.Agent;
import model.Map;
import model.input.DecisionNumeric;

public class RandomValue extends DecisionNumeric {

	private static int seed;
	
	public RandomValue() {
		this(Game.RANDOM_SEED);
	}
	
	public RandomValue(int seed) {
		setSeed(seed);
	}
	
	public static int getSeed() {
		return seed;
	}

	public static void setSeed(int seed) {
		RandomValue.seed = seed;
	}

	@Override
	public int decide(Agent agent, Map map) {
		//Random rnd = new Random(getSeed());
		Random rnd = new Random();
		return rnd.nextInt(100);
	}

	public String toString() {
		String output = Option.RANDOM.toString();
		return output;
	}
}
