package model.output;

import java.io.ByteArrayOutputStream;
import java.io.PrintStream;

import org.junit.After;
import org.junit.Test;

import junit.framework.TestCase;
import main.Game;
import model.Agent;
import model.Map;
import model.output.Action.Activity;
import readers.ActionReaderImpl;
import readers.CriteriaReaderImpl;
import readers.GameReader;
import readers.GameReaderImpl;
import readers.InputReaderImpl;
import readers.MapReaderImpl;
import readers.ModeReaderImpl;
import readers.PlantReaderImpl;
import readers.PlayerReaderImpl;
import readers.PositionReaderImpl;
import readers.TreeReaderImpl;

public class TestLiftFood extends TestCase {

	private GameReader gameReader;
	private final ByteArrayOutputStream outContent = new ByteArrayOutputStream();

	@Override
	protected void setUp() {
		gameReader = new GameReaderImpl(new MapReaderImpl(new PlantReaderImpl(),
				new PlayerReaderImpl(new TreeReaderImpl(new ActionReaderImpl(new PositionReaderImpl()), new InputReaderImpl(new PositionReaderImpl()))),
				new CriteriaReaderImpl(new ActionReaderImpl(new PositionReaderImpl())), new ModeReaderImpl()));
		System.setOut(new PrintStream(outContent));
	}
	
	@After
	public void cleanUpStreams() {
	    System.setOut(null);
	}

	/**
	 * http://stackoverflow.com/questions/1119385/junit-test-for-system-out-println
	 */
	@Test
	public void testLiftFood_Success_AllFoodFull() {
		String file = "resources\\test\\outputMaps\\test_liftFood_success_allFoodFull.map";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		
		assertTrue(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.LIFT_FOOD);
		assertTrue(map.getTile(agent.getCurrentPos()).getFood() == 0);
		assertTrue(agent.getFood() == Agent.PICKUP_FOOD);
	}
	
	@Test
	public void testLiftFood_Success_PartialFood() {
		String file = "resources\\test\\outputMaps\\test_liftFood_success_partialFood.map";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		int dirt = map.getTile(agent.getCurrentPos()).getFood();
		
		assertTrue(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.LIFT_FOOD);
		assertTrue(map.getTile(agent.getCurrentPos()).getFood() == dirt - agent.getFood());
		assertTrue(agent.getFood() == Agent.PICKUP_FOOD);
	}
	
	@Test
	public void testLiftFood_Success_AllFoodNotFull() {
		String file = "resources\\test\\outputMaps\\test_liftFood_success_allFoodNotFull.map";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		
		assertTrue(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.LIFT_FOOD);
		assertTrue(map.getTile(agent.getCurrentPos()).getFood() == 0);
		assertTrue(agent.getFood() < Agent.PICKUP_FOOD);
	}
	
	@Test
	public void testLiftFood_Success_HasFood() {
		String file = "resources\\test\\outputMaps\\test_liftFood_success_hasFood.map";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		int agentFood = 1;
		int food = map.getTile(agent.getCurrentPos()).getFood();
		agent.setFood(agentFood);
		
		assertTrue(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.LIFT_FOOD);
		assertTrue(map.getTile(agent.getCurrentPos()).getFood() == (food - (Agent.PICKUP_FOOD - agentFood)));
		assertTrue(agent.getFood() == Agent.PICKUP_FOOD);
	}
	
	@Test
	public void testLiftFood_Fail_NoFood() {
		String file = "resources\\test\\outputMaps\\test_liftFood_fail_noFood.map";
		String error = "Cannot LIFT_FOOD because no food left on map\r\n";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		
		assertFalse(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.LIFT_FOOD);
		assertTrue(map.getTile(agent.getCurrentPos()).getFood() == 0);
		assertEquals(outContent.toString(), error);
	}
	
	@Test
	public void testLiftFood_Fail_HasDirt() {
		String file = "resources\\test\\outputMaps\\test_liftFood_fail_hasFood.map";
		String error = "Cannot LIFT_FOOD because agent already has dirt\r\n";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		agent.setDirt(Agent.PICKUP_DIRT);
		int food = map.getTile(agent.getCurrentPos()).getFood();
		
		assertFalse(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.LIFT_FOOD);
		assertTrue(map.getTile(agent.getCurrentPos()).getFood() == food);
		assertEquals(outContent.toString(), error);
	}
	
	@Test
	public void testLiftFood_Fail_HasFood() {
		String file = "resources\\test\\outputMaps\\test_liftFood_fail_hasFood.map";
		String error = "Cannot LIFT_FOOD because agent already has maximum food\r\n";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		agent.setFood(Agent.PICKUP_FOOD);
		int food = map.getTile(agent.getCurrentPos()).getFood();
		
		assertFalse(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.LIFT_FOOD);
		assertTrue(map.getTile(agent.getCurrentPos()).getFood() == food);
		assertEquals(outContent.toString(), error);
	}
	
	@Test
	public void test_ToString() {
		LiftFood output = new LiftFood();
		String strOutput = "LIFT_FOOD";
		assertTrue(output.toString().equals(strOutput));
	}
	
}
